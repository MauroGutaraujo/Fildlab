from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class PrediccionRul(Base):
    __tablename__ = "predicciones_rul"
    __table_args__ = (
        CheckConstraint("nivel_alerta IN ('VERDE', 'AMARILLO', 'ROJO')", name="predicciones_rul_nivel_check"),
    )

    equipo_serie: Mapped[str] = mapped_column(String(50), ForeignKey("equipos.serie"), primary_key=True)
    dias_vida_util_remanente: Mapped[int] = mapped_column(Integer)
    nivel_alerta: Mapped[str] = mapped_column(String(20))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
