from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

# YYYY-MM, mes 01-12 — mismo mecanismo que app/schemas/common.py:Ruc
Periodo = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


class ContratoRentabilidadOut(BaseModel):
    contrato_id: int
    cliente_ruc: str
    razon_social: str
    ingreso_soles: Decimal
    costo_repuestos_soles: Decimal
    margen_soles: Decimal
    margen_pct: float | None
    historial_completo: bool = False


class RentabilidadOut(BaseModel):
    periodo: str
    contratos: list[ContratoRentabilidadOut]


class OrdenFueraSlaOut(BaseModel):
    orden_id: UUID
    equipo_serie: str | None
    razon_social: str
    tiempo_respuesta_horas: Decimal
    sla_horas_max_respuesta: int


class SlaOut(BaseModel):
    periodo: str
    total_ordenes: int
    ordenes_sin_medicion: int
    ordenes_fuera_sla: list[OrdenFueraSlaOut]
    pct_cumplimiento: float | None
