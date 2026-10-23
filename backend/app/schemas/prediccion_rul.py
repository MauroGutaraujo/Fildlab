from datetime import date, datetime, timezone
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.politica_rul import POLITICA_ALERTA, VERSION_CALCULO, VERSION_DATASET, nivel_alerta

NivelAlerta = Literal["VERDE", "AMARILLO", "ROJO"]


class PrediccionRulOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipo_serie: str
    dias_vida_util_remanente: int | None = Field(default=None, ge=0)
    nivel_alerta: NivelAlerta | None = None
    actualizado_en: datetime
    version_calculo: str = "LEGADO"
    motivo_no_estimable: str | None = None
    estado_estimacion: Literal["ESTIMADA", "NO_ESTIMABLE", "REQUIERE_RECALCULO", "VENCIDA"] = "REQUIERE_RECALCULO"
    experimental: Literal[True] = True
    origen_datos: Literal["SINTETICOS"] = "SINTETICOS"
    politica_alerta: str = POLITICA_ALERTA
    version_dataset: str | None = None
    fecha_referencia: date | None = None
    tipo_referencia: str | None = None
    ejecucion_id: UUID | None = None
    vence_en: datetime | None = None
    alcance_estimacion: Literal["SISTEMA_DESDE_INSTALACION"] | None = None

    @model_validator(mode="after")
    def presentar_solo_calculo_corregido(self):
        self.version_dataset = VERSION_DATASET if self.version_calculo == VERSION_CALCULO else None
        self.alcance_estimacion = "SISTEMA_DESDE_INSTALACION" if self.version_calculo == VERSION_CALCULO else None
        if (self.version_calculo != VERSION_CALCULO or self.fecha_referencia is None
                or self.tipo_referencia is None or self.ejecucion_id is None or self.vence_en is None
                or self.actualizado_en.tzinfo is None or self.vence_en.tzinfo is None
                or self.actualizado_en > datetime.now(timezone.utc)
                or self.vence_en <= self.actualizado_en
                or self.motivo_no_estimable == "REQUIERE_RECALCULO"):
            self.estado_estimacion = "REQUIERE_RECALCULO"
            self.motivo_no_estimable = "REQUIERE_RECALCULO"
        elif datetime.now(timezone.utc) >= self.vence_en:
            self.estado_estimacion = "VENCIDA"
        elif self.motivo_no_estimable is not None or self.dias_vida_util_remanente is None:
            self.estado_estimacion = "NO_ESTIMABLE"
            self.motivo_no_estimable = self.motivo_no_estimable or "RESULTADO_INVALIDO"
        else:
            self.estado_estimacion = "ESTIMADA"
            self.nivel_alerta = nivel_alerta(self.dias_vida_util_remanente)
            return self
        self.dias_vida_util_remanente = None
        self.nivel_alerta = None
        return self
