import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class OrdenServicio(Base):
    __tablename__ = "ordenes_servicio"
    __table_args__ = (
        CheckConstraint("estado IN ('SINCRONIZADA', 'COMPROMETIDA', 'LIQUIDADA')", name="ordenes_estado_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    contrato_id: Mapped[int | None] = mapped_column(ForeignKey("contratos.id"))
    equipo_serie: Mapped[str | None] = mapped_column(String(50), ForeignKey("equipos.serie"))
    tecnico_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    tipo_intervencion: Mapped[str] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20), server_default="SINCRONIZADA", default="SINCRONIZADA")
    fecha_creacion_cliente: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_sincronizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tiempo_respuesta_horas: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))


class ActaInmutable(Base):
    __tablename__ = "actas_inmutables"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_servicio.id"), unique=True)
    payload_raw: Mapped[str] = mapped_column(Text)
    hash_sha256: Mapped[str] = mapped_column(String(64))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    firma_base64: Mapped[str] = mapped_column(Text)
    gps_latitud: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    gps_longitud: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdendaCorreccion(Base):
    __tablename__ = "adendas_correccion"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_servicio.id"))
    gerente_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    observacion: Mapped[str] = mapped_column(Text)
    ajuste_repuestos: Mapped[list | None] = mapped_column(JSONB)
    fecha_adenda: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
