from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Ruc
from app.schemas.inventario import Codigo

Precio = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class VentaItemIn(BaseModel):
    repuesto_codigo: Codigo
    cantidad: Annotated[int, Field(gt=0)]
    precio_unitario_soles: Precio


class VentaIn(BaseModel):
    cliente_ruc: Ruc
    items: Annotated[list[VentaItemIn], Field(min_length=1)]


class VentaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    repuesto_codigo: str
    cantidad: int
    precio_unitario_soles: Decimal


class VentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_ruc: str
    usuario_id: int
    total_soles: Decimal
    fecha: datetime
    items: list[VentaItemOut]
