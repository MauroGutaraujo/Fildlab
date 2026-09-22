from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.common import Ruc

Serie = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
NoNegativo = Annotated[float, Field(ge=0)]
Ph = Annotated[float, Field(ge=0, le=14)]


class ParametrosNominales(BaseModel):
    """REQ-03: ficha técnica del equipo. Los 8 parámetros de referencia son obligatorios
    para los tres tipos de sistema (el spec no los condiciona por tipo_sistema); se admiten
    campos adicionales para no bloquear datos extra que un técnico quiera anotar."""

    model_config = ConfigDict(extra="allow")

    tds_entrada_ppm: NoNegativo
    tds_post_membrana_ppm: NoNegativo
    tds_producto_final_ppm: NoNegativo
    ph: Ph
    conductividad_us_cm: NoNegativo
    resistividad_mohm_cm: NoNegativo
    litros_consumidos_red: NoNegativo
    litros_agua_pura: NoNegativo


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
    parametros_nominales: ParametrosNominales

    _fecha = field_validator("fecha_instalacion")(_no_futura)


class EquipoUpdate(BaseModel):
    contrato_id: int | None = None
    fecha_instalacion: date | None = None
    # Reemplazo completo, no parche: si se envía, debe traer el set completo de REQ-03.
    parametros_nominales: ParametrosNominales | None = None

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
