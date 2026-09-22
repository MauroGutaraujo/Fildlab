from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Venta(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_ruc: Mapped[str] = mapped_column(String(11), ForeignKey("clientes.ruc"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    total_soles: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["VentaItem"]] = relationship(back_populates="venta", lazy="selectin", order_by="VentaItem.id")


class VentaItem(Base):
    __tablename__ = "ventas_items"
    __table_args__ = (CheckConstraint("cantidad > 0", name="ventas_items_cantidad_check"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"))
    repuesto_codigo: Mapped[str] = mapped_column(String(30), ForeignKey("repuestos.codigo"))
    cantidad: Mapped[int]
    precio_unitario_soles: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    venta: Mapped[Venta] = relationship(back_populates="items")
