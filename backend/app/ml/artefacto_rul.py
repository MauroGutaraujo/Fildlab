"""Formato de datos cerrado para el modelo actual, sin deserialización ejecutable."""
import hashlib
import json
import os
import re
from importlib.metadata import version, PackageNotFoundError
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.core.politica_rul import POLITICA_ALERTA, VERSION_CALCULO, VERSION_DATASET
from app.ml.modelo_rul import ajustar_modelo
from app.ml.registro_rul import entorno_calculo, huella_dataset
from app.models.equipo import TIPOS_SISTEMA

RAIZ = Path(__file__).resolve().parent / "recursos"
MAX_BYTES = 4 * 1024 * 1024


class ModeloInvalido(ValueError):
    pass


class Cerrado(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class Curva(Cerrado):
    tiempos: list[float] = Field(min_length=1, max_length=100_000)
    supervivencia: list[float] = Field(min_length=1, max_length=100_000)
    soporte: float = Field(gt=0)

    @model_validator(mode="after")
    def coherencia(self):
        t, s = np.array(self.tiempos), np.array(self.supervivencia)
        if (len(t) != len(s) or (t < 0).any() or (np.diff(t) <= 0).any()
                or (s < 0).any() or (s > 1).any() or (np.diff(s) > 1e-12).any()
                or self.soporte < t[0] or self.soporte > t[-1]):
            raise ValueError("Curva inválida")
        return self


class Resumen(Cerrado):
    filas: int = Field(gt=0)
    eventos: int = Field(ge=0)

    @model_validator(mode="after")
    def coherencia(self):
        if self.eventos > self.filas:
            raise ValueError("Eventos superiores al número de filas")
        return self


class Artefacto(Cerrado):
    formato: Literal["CURVAS_COX_V1"]
    origen: Literal["SINTETICOS"]
    alcance: Literal["SISTEMA_DESDE_INSTALACION"]
    validacion: Literal["TECNICA_SIN_VALIDACION_DE_CAMPO"]
    entrenado_en: AwareDatetime
    version_calculo: str
    version_dataset: str
    politica_alerta: str
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    constraints_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entorno: dict[str,str]
    resumen: Resumen
    curvas: dict[str,Curva]

    @model_validator(mode="after")
    def contrato(self):
        if (self.version_calculo != VERSION_CALCULO or self.version_dataset != VERSION_DATASET
                or self.politica_alerta != POLITICA_ALERTA or set(self.curvas) != set(TIPOS_SISTEMA)):
            raise ValueError("Contrato de modelo incompatible")
        return self


@dataclass(frozen=True)
class ModeloPublicado:
    metadatos: Artefacto
    sha256: str
    advertencias: tuple[str,...] = ()

    @property
    def soporte_por_tipo(self):
        return {t:c.soporte for t,c in self.metadatos.curvas.items()}

    def curva(self,tipo: str) -> pd.Series:
        c = self.metadatos.curvas[tipo]
        return pd.Series(c.supervivencia,index=c.tiempos)


def _constraints_sha256():
    # Normalizar EOL para que checkout Windows/Linux represente el mismo contrato.
    datos=(RAIZ/"constraints-ml.txt").read_text(encoding="utf-8").replace("\r\n","\n")
    return hashlib.sha256(datos.encode()).hexdigest()


def _verificar_dependencias():
    for linea in (RAIZ/"constraints-ml.txt").read_text(encoding="utf-8").splitlines():
        if not linea.strip() or linea.startswith("#"):
            continue
        nombre, esperado = linea.split("==")
        if version(nombre) != esperado:
            raise ModeloInvalido("Versiones ML incompatibles con el modelo")


def exportar_modelo(dataset: pd.DataFrame, destino: str | Path) -> str:
    _verificar_dependencias()
    modelo=ajustar_modelo(dataset)
    if modelo.advertencias or modelo.ajuste is None:
        raise ModeloInvalido("No se publica un ajuste inestable")
    try:
        curvas={}
        for tipo in TIPOS_SISTEMA:
            serie=modelo.curva(tipo)
            curvas[tipo]=Curva(tiempos=serie.index.tolist(),supervivencia=serie.tolist(),soporte=modelo.soporte_por_tipo[tipo])
        a=Artefacto(formato="CURVAS_COX_V1",origen="SINTETICOS",alcance="SISTEMA_DESDE_INSTALACION",
            validacion="TECNICA_SIN_VALIDACION_DE_CAMPO",entrenado_en=datetime.now(timezone.utc), version_calculo=VERSION_CALCULO,
            version_dataset=VERSION_DATASET, politica_alerta=POLITICA_ALERTA,
            dataset_sha256=huella_dataset(dataset),constraints_sha256=_constraints_sha256(),entorno=entorno_calculo(),
            resumen={"filas":len(dataset),"eventos":int(dataset.evento.sum())},curvas=curvas)
    except (ValueError, KeyError) as exc:
        raise ModeloInvalido("No se puede publicar este modelo") from exc
    datos=json.dumps(a.model_dump(mode="json"),ensure_ascii=False,allow_nan=False,separators=(",",":"),sort_keys=True).encode()
    if len(datos)>MAX_BYTES:
        raise ModeloInvalido("Modelo demasiado grande")
    # Nunca sustituir un artefacto existente; activar es un paso explícito separado.
    with Path(destino).open("xb") as f:
        f.write(datos)
    return hashlib.sha256(datos).hexdigest()


def _sin_duplicados(pares):
    d={}
    for k,v in pares:
        if k in d: raise ValueError("Clave JSON repetida")
        d[k]=v
    return d


def cargar_modelo(ruta: str | Path | None=None, esperado: str | None=None) -> ModeloPublicado:
    try:
        if ruta is None:
            ruta=os.environ.get("RUL_MODELO_PATH")
            esperado=os.environ.get("RUL_MODELO_SHA256")
            if not ruta and not esperado:
                manifiesto=json.loads((RAIZ/"modelos"/"activo.json").read_text(),object_pairs_hook=_sin_duplicados)
                if set(manifiesto)!={"archivo","sha256"} or Path(manifiesto["archivo"]).name != manifiesto["archivo"]:
                    raise ValueError("Manifiesto inválido")
                ruta=RAIZ/"modelos"/manifiesto["archivo"]
                esperado=manifiesto["sha256"]
        if not ruta or not esperado or not re.fullmatch(r"[0-9a-f]{64}",esperado):
            raise ValueError("Se requiere ruta y huella de modelo")
        with Path(ruta).open("rb") as f:
            datos=f.read(MAX_BYTES+1)
        if len(datos)>MAX_BYTES or hashlib.sha256(datos).hexdigest()!=esperado:
            raise ValueError("Integridad del modelo inválida")
        json.loads(datos,object_pairs_hook=_sin_duplicados)
        a=Artefacto.model_validate_json(datos)
        _verificar_dependencias()
        if a.entorno != entorno_calculo() or a.constraints_sha256 != _constraints_sha256():
            raise ValueError("Entorno del modelo incompatible")
        return ModeloPublicado(a,esperado)
    except (OSError, ValueError, TypeError, KeyError, ValidationError, PackageNotFoundError) as exc:
        raise ModeloInvalido("Modelo ausente, alterado o incompatible") from exc
