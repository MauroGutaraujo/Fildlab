from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Observacion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
TipoComponente = Literal["MEMBRANA", "FILTRO", "RESINA", "OTRO"]
TipoIntervencion = Literal["INSPECCION", "LIMPIEZA", "REPARACION_PARCIAL", "SUSTITUCION"]


class ComponenteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Nombre
    tipo_componente: TipoComponente
    fecha_instalacion: date | None = None
    fabricante_modelo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] | None = None


class ComponenteOut(ComponenteIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    equipo_serie: str
    creado_por_id: int
    creado_en: datetime
    revision: int
    anulado_en: datetime | None
    ciclo_actual_desde: date | None


class CambioComponenteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    solicitud_id: UUID
    revision_esperada: StrictInt = Field(ge=1)
    motivo: Observacion


class CorregirComponenteIn(CambioComponenteIn, ComponenteIn):
    pass


class RestablecerComponenteIn(CambioComponenteIn, ComponenteIn):
    pass


class CambioComponenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    solicitud_id: UUID
    componente_id: UUID
    accion: Literal["CORREGIR", "ANULAR_ALTA", "RESTABLECER_ALTA"]
    revision_anterior: int
    revision_nueva: int
    antes: dict[str, Any]
    despues: dict[str, Any]
    solicitud: dict[str, Any]
    motivo: str
    registrado_por_id: int
    registrado_en: datetime


class IntervencionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    orden_id: UUID
    tipo: TipoIntervencion
    fecha_efectiva: date
    observacion: Observacion


class AnulacionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo: Observacion


class AnulacionOut(AnulacionIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    intervencion_id: UUID
    registrado_por_id: int
    registrado_en: datetime


class IntervencionOut(IntervencionIn):
    model_config = ConfigDict(from_attributes=True)
    componente_id: UUID
    acta_hash: str
    registrado_por_id: int
    registrado_por_nombre: str
    registrado_en: datetime
    anulacion: AnulacionOut | None


class OrdenFirmadaOut(BaseModel):
    id: UUID
    tipo_intervencion: str
    fecha_creacion_cliente: datetime


class AnularAltaIn(CambioComponenteIn):
    pass
