import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import NonBlank
from app.schemas.inventario import Codigo

# Duplicados deliberadamente de app/schemas/equipo.py: una lectura de una orden no es
# lo mismo que la ficha técnica de referencia de un equipo, aunque comparten forma.
NoNegativo = Annotated[float, Field(ge=0)]
Ph = Annotated[float, Field(ge=0, le=14)]


class LecturasAgua(BaseModel):
    """RN-02: los 8 parámetros físico-químicos y volumétricos obligatorios para cerrar una orden."""

    tds_entrada_ppm: NoNegativo
    tds_post_membrana_ppm: NoNegativo
    tds_producto_final_ppm: NoNegativo
    ph: Ph
    conductividad_us_cm: NoNegativo
    resistividad_mohm_cm: NoNegativo
    litros_consumidos_red: NoNegativo
    litros_agua_pura: NoNegativo


class RepuestoConsumidoIn(BaseModel):
    repuesto_codigo: Codigo
    cantidad: Annotated[int, Field(gt=0)]


class OrdenSincronizarIn(BaseModel):
    id: uuid.UUID
    contrato_id: int
    equipo_serie: str
    tecnico_id: int
    tipo_intervencion: NonBlank
    fecha_creacion_cliente: datetime
    lecturas_agua: LecturasAgua
    firma_base64: NonBlank
    gps_latitud: Decimal
    gps_longitud: Decimal
    repuestos_consumidos: list[RepuestoConsumidoIn] = []

    model_config = ConfigDict(extra="ignore")
