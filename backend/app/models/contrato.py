from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Contrato(Base):
    __tablename__ = "contratos"
    __table_args__ = (
        CheckConstraint("fecha_fin >= fecha_inicio", name="contratos_fechas_check"),
        CheckConstraint("monto_mensual_soles > 0", name="contratos_monto_check"),
        CheckConstraint("sla_horas_max_respuesta > 0", name="contratos_sla_check"),
        CheckConstraint("estado IN ('ACTIVO', 'VENCIDO', 'ANULADO')", name="contratos_estado_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_ruc: Mapped[str] = mapped_column(String(11), ForeignKey("clientes.ruc"), index=True)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    monto_mensual_soles: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    sla_horas_max_respuesta: Mapped[int] = mapped_column(server_default="4", default=4)
    estado: Mapped[str] = mapped_column(String(20), server_default="ACTIVO", default="ACTIVO")
