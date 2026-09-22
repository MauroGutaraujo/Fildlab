import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Codigo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
Descripcion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Costo = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class RepuestoIn(BaseModel):
    codigo: Codigo
    descripcion: Descripcion
    costo_unitario_soles: Costo


class RepuestoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    stock_almacen_central: int
    costo_unitario_soles: Decimal


class MovimientoIn(BaseModel):
    repuesto_codigo: Codigo
    # SALIDA_VENTA solo la genera el módulo de ventas.
    tipo: Literal["ENTRADA", "SALIDA_ORDEN", "AJUSTE_ENTRADA", "AJUSTE_SALIDA"]
    cantidad: Annotated[int, Field(gt=0)]
    orden_id: uuid.UUID | None = None


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repuesto_codigo: str
    tipo: str
    cantidad: int
    orden_id: uuid.UUID | None
    venta_id: int | None
    usuario_id: int
    creado_en: datetime
