from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.common import Ruc

Serie = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Parametros = Annotated[dict[str, Any], Field(min_length=1)]


def _no_futura(v: date) -> date:
    if v > date.today():
        raise ValueError("La fecha de instalación no puede ser futura")
    return v


class EquipoIn(BaseModel):
    serie: Serie
    cliente_ruc: Ruc
    contrato_id: int | None = None
    tipo_sistema: Literal["OSMOSIS_INVERSA", "ABLANDADOR", "FILTRO"]
    fecha_instalacion: date
    parametros_nominales: Parametros

    _fecha = field_validator("fecha_instalacion")(_no_futura)


class EquipoUpdate(BaseModel):
    contrato_id: int | None = None
    fecha_instalacion: date | None = None
    parametros_nominales: Parametros | None = None

    @field_validator("fecha_instalacion")
    @classmethod
    def _fecha(cls, v: date | None) -> date | None:
        return None if v is None else _no_futura(v)


class EquipoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serie: str
    cliente_ruc: str
    contrato_id: int | None
    tipo_sistema: str
    fecha_instalacion: date
    parametros_nominales: dict[str, Any]
