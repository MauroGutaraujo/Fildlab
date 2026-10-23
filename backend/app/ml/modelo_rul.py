from dataclasses import dataclass
from datetime import date
import warnings
from typing import Protocol

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.exceptions import ConvergenceError, ConvergenceWarning

from app.core.politica_rul import nivel_alerta  # reexport para consumidores existentes
from app.models.equipo import TIPOS_SISTEMA


class ParametrosImposibles(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


class ModeloSupervivencia(Protocol):
    @property
    def soporte_por_tipo(self) -> dict[str,float]: ...
    @property
    def advertencias(self) -> tuple[str,...]: ...
    def curva(self,tipo_sistema: str) -> pd.Series: ...


@dataclass(frozen=True)
class ModeloRul:
    ajuste: CoxPHFitter | None
    soporte_por_tipo: dict[str, float]
    advertencias: tuple[str, ...] = ()

    def curva(self, tipo_sistema: str) -> pd.Series:
        if self.ajuste is None or self.advertencias:
            raise ParametrosImposibles("MODELO_INESTABLE")
        fila = pd.DataFrame(0, index=[0], columns=self.ajuste.params_.index, dtype=float)
        columna = f"tipo_sistema_{tipo_sistema}"
        if columna in fila.columns:
            fila[columna] = 1.0
        return self.ajuste.predict_survival_function(fila).iloc[:, 0]


def ajustar_modelo(dataset: pd.DataFrame) -> ModeloRul:
    columnas = {"duracion_dias", "evento", "tipo_sistema"}
    if (not isinstance(dataset, pd.DataFrame) or dataset.empty
            or not dataset.columns.is_unique or set(dataset.columns) != columnas):
        raise ValueError("Dataset inválido: se esperan duración, evento y tipo de sistema")
    if (dataset.isna().any().any()
            or not pd.api.types.is_numeric_dtype(dataset["duracion_dias"])
            or pd.api.types.is_bool_dtype(dataset["duracion_dias"])
            or not pd.api.types.is_numeric_dtype(dataset["evento"])
            or not dataset["evento"].isin([0, 1]).all()
            or not dataset["tipo_sistema"].isin(TIPOS_SISTEMA).all()):
        raise ValueError("Dataset inválido: valores fuera del contrato")
    numeros = dataset[["duracion_dias", "evento"]].to_numpy(dtype=float)
    if not np.isfinite(numeros).all() or (dataset["duracion_dias"] <= 0).any():
        raise ValueError("Dataset inválido: duración no positiva o no finita")
    soporte = dataset.groupby("tipo_sistema")["duracion_dias"].max().to_dict()
    df = pd.get_dummies(dataset, columns=["tipo_sistema"], drop_first=True)
    cph = CoxPHFitter()
    try:
        with warnings.catch_warnings(record=True) as capturadas:
            warnings.simplefilter("always", ConvergenceWarning)
            cph.fit(df, duration_col="duracion_dias", event_col="evento")
    except ConvergenceError as exc:
        return ModeloRul(None, soporte, (str(exc),))
    relevantes = []
    for aviso in capturadas:
        if issubclass(aviso.category, ConvergenceWarning):
            relevantes.append(str(aviso.message))
        else:
            warnings.warn(aviso.message, aviso.category, stacklevel=2)
    if not np.isfinite(cph.params_.to_numpy()).all():
        relevantes.append("Coeficientes no finitos")
    return ModeloRul(cph, soporte, tuple(relevantes))


def mediana_condicional(curva: pd.Series, *, edad: float, limite: float) -> float:
    """Cuantil de la curva escalonada S(t)/S(edad), sin extrapolación.

    El primer salto que alcanza S(edad)/2 define el cuantil. Antes del
    primer punto observado se toma S=1. No interpolamos entre eventos.
    """
    tiempos = curva.index.to_numpy(dtype=float)
    valores = curva.to_numpy(dtype=float)
    if (not np.isfinite(edad) or edad < 0 or not np.isfinite(limite) or limite <= 0
            or len(tiempos) == 0 or not np.isfinite(tiempos).all()
            or not np.isfinite(valores).all() or (tiempos < 0).any()
            or (np.diff(tiempos) <= 0).any() or (valores < 0).any()
            or (valores > 1).any() or (np.diff(valores) > 1e-12).any()):
        raise ParametrosImposibles("CURVA_INVALIDA")
    if edad >= limite:
        raise ParametrosImposibles("EDAD_FUERA_SOPORTE")
    posicion = np.searchsorted(tiempos, edad, side="right") - 1
    supervivencia = valores[posicion] if posicion >= 0 else 1.0
    if supervivencia <= 0:
        raise ParametrosImposibles("SUPERVIVENCIA_NULA")
    cruces = tiempos[(tiempos > edad) & (tiempos <= limite) & (valores <= supervivencia / 2)]
    if len(cruces) == 0:
        raise ParametrosImposibles("MEDIANA_FUERA_SOPORTE")
    return float(cruces[0] - edad)


def calificar_equipo(modelo: ModeloSupervivencia, tipo_sistema: str, fecha_instalacion: date, hoy: date) -> dict:
    """Estimación experimental; ParametrosImposibles significa abstención."""
    if tipo_sistema not in modelo.soporte_por_tipo:
        raise ParametrosImposibles("TIPO_DESCONOCIDO")
    dias_en_servicio = (hoy - fecha_instalacion).days
    if dias_en_servicio < 0:
        raise ParametrosImposibles("FECHA_FUTURA")
    if modelo.advertencias:
        raise ParametrosImposibles("MODELO_INESTABLE")
    curva = modelo.curva(tipo_sistema)
    restantes = mediana_condicional(curva, edad=dias_en_servicio, limite=modelo.soporte_por_tipo[tipo_sistema])
    dias = round(restantes)
    return {"dias_vida_util_remanente": dias, "nivel_alerta": nivel_alerta(dias)}
