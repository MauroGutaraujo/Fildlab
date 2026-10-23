from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models import Base


class PrediccionRul(Base):
    __tablename__ = "predicciones_rul"
    __table_args__ = (
        CheckConstraint("nivel_alerta IN ('VERDE', 'AMARILLO', 'ROJO')", name="predicciones_rul_nivel_check"),
        CheckConstraint(
            "(dias_vida_util_remanente IS NOT NULL AND dias_vida_util_remanente >= 0 AND nivel_alerta IS NOT NULL AND motivo_no_estimable IS NULL) "
            "OR (dias_vida_util_remanente IS NULL AND nivel_alerta IS NULL AND motivo_no_estimable IS NOT NULL)",
            name="predicciones_rul_resultado_check",
        ),
    )

    equipo_serie: Mapped[str] = mapped_column(String(50), ForeignKey("equipos.serie"), primary_key=True)
    dias_vida_util_remanente: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nivel_alerta: Mapped[str | None] = mapped_column(String(20), nullable=True)
    version_calculo: Mapped[str] = mapped_column(String(40), nullable=False, server_default="LEGADO")
    motivo_no_estimable: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fecha_referencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    tipo_referencia: Mapped[str | None] = mapped_column(String(50))
    ejecucion_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ejecuciones_rul.id"))
    vence_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
