import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ComponenteEquipo(Base):
    __tablename__ = "componentes_equipo"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipo_serie: Mapped[str] = mapped_column(String(50), ForeignKey("equipos.serie"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    tipo_componente: Mapped[str] = mapped_column(String(20))
    fecha_instalacion: Mapped[date | None] = mapped_column(Date)
    fabricante_modelo: Mapped[str | None] = mapped_column(String(120))
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("tipo_componente IN ('MEMBRANA','FILTRO','RESINA','OTRO')", name="componentes_tipo_check"),
        CheckConstraint("length(btrim(nombre)) > 0", name="componentes_nombre_check"),
        CheckConstraint("revision >= 1", name="componentes_revision_check"),
        Index("componentes_equipo_nombre_key", equipo_serie, func.lower(nombre), unique=True, postgresql_where=anulado_en.is_(None)),
    )


class IntervencionComponente(Base):
    __tablename__ = "intervenciones_componente"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    componente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("componentes_equipo.id"), index=True)
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_servicio.id"), index=True)
    acta_hash: Mapped[str] = mapped_column(String(64))
    tipo: Mapped[str] = mapped_column(String(30))
    fecha_efectiva: Mapped[date] = mapped_column(Date)
    observacion: Mapped[str] = mapped_column(Text)
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("tipo IN ('INSPECCION','LIMPIEZA','REPARACION_PARCIAL','SUSTITUCION')", name="intervenciones_tipo_check"),
        CheckConstraint("length(btrim(observacion)) > 0", name="intervenciones_observacion_check"),
    )


class AnulacionIntervencion(Base):
    __tablename__ = "anulaciones_intervencion"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intervencion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("intervenciones_componente.id"), unique=True)
    motivo: Mapped[str] = mapped_column(Text)
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("length(btrim(motivo)) > 0", name="anulaciones_motivo_check"),)


class CambioComponente(Base):
    __tablename__ = "cambios_componentes"
    solicitud_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    componente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("componentes_equipo.id"), index=True)
    accion: Mapped[str] = mapped_column(String(24))
    revision_anterior: Mapped[int] = mapped_column(Integer)
    revision_nueva: Mapped[int] = mapped_column(Integer)
    antes: Mapped[dict] = mapped_column(JSONB)
    despues: Mapped[dict] = mapped_column(JSONB)
    solicitud: Mapped[dict] = mapped_column(JSONB)
    motivo: Mapped[str] = mapped_column(Text)
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("accion IN ('CORREGIR','ANULAR_ALTA','RESTABLECER_ALTA')", name="cambios_componentes_accion_check"),
        CheckConstraint("revision_nueva = revision_anterior + 1", name="cambios_componentes_revision_check"),
        CheckConstraint("length(btrim(motivo)) > 0", name="cambios_componentes_motivo_check"),
        UniqueConstraint("componente_id", "revision_nueva", name="cambios_componentes_revision_key"),
    )
