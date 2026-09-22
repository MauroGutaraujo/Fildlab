import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

TIPOS_MOVIMIENTO = ("ENTRADA", "SALIDA_ORDEN", "SALIDA_VENTA", "AJUSTE_ENTRADA", "AJUSTE_SALIDA")


class Repuesto(Base):
    __tablename__ = "repuestos"
    __table_args__ = (
        CheckConstraint("stock_almacen_central >= 0", name="repuestos_stock_check"),
        CheckConstraint("costo_unitario_soles >= 0", name="repuestos_costo_check"),
    )

    codigo: Mapped[str] = mapped_column(String(30), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(150))
    stock_almacen_central: Mapped[int] = mapped_column(server_default="0", default=0)
    costo_unitario_soles: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="movimientos_cantidad_check"),
        CheckConstraint(
            "tipo IN ('ENTRADA','SALIDA_ORDEN','SALIDA_VENTA','AJUSTE_ENTRADA','AJUSTE_SALIDA')",
            name="movimientos_tipo_check",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repuesto_codigo: Mapped[str] = mapped_column(String(30), ForeignKey("repuestos.codigo"))
    tipo: Mapped[str] = mapped_column(String(20))
    cantidad: Mapped[int]
    orden_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ordenes_servicio.id"))
    venta_id: Mapped[int | None] = mapped_column(ForeignKey("ventas.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
