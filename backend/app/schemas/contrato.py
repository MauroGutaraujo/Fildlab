from datetime import date
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Ruc

Monto = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
Horas = Annotated[int, Field(gt=0, le=8760)]


class _Vigencia(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    monto_mensual_soles: Monto
    sla_horas_max_respuesta: Horas = 4

    @model_validator(mode="after")
    def _fechas_coherentes(self) -> Self:
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class ContratoIn(_Vigencia):
    cliente_ruc: Ruc


class ContratoUpdate(_Vigencia):
    pass


class ContratoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_ruc: str
    fecha_inicio: date
    fecha_fin: date
    monto_mensual_soles: Decimal
    sla_horas_max_respuesta: int
    estado: str
