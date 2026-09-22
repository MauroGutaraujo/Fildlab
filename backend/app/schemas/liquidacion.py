import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import NonBlank
from app.schemas.inventario import Codigo

EstadoOrden = Literal["SINCRONIZADA", "COMPROMETIDA", "LIQUIDADA"]


class OrdenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contrato_id: int | None
    equipo_serie: str | None
    tecnico_id: int | None
    tipo_intervencion: str
    estado: EstadoOrden
    fecha_creacion_cliente: datetime
    fecha_sincronizacion: datetime
    tiempo_respuesta_horas: Decimal | None


class AjusteRepuesto(BaseModel):
    """delta > 0 devuelve stock al almacén central; delta < 0 lo descuenta."""

    repuesto_codigo: Codigo
    delta: int

    @field_validator("delta")
    @classmethod
    def _delta_distinto_de_cero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("delta no puede ser 0")
        return v


class AdendaIn(BaseModel):
    observacion: NonBlank
    ajuste_repuestos: list[AjusteRepuesto] | None = None


class AdendaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    orden_id: uuid.UUID
    gerente_id: int
    observacion: str
    ajuste_repuestos: list[dict] | None
    fecha_adenda: datetime
