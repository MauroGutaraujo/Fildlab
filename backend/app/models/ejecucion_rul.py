from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class EjecucionRul(Base):
    __tablename__ = "ejecuciones_rul"
    __table_args__ = (
        CheckConstraint("estado IN ('EN_CURSO','COMPLETADA','FALLIDA','OMITIDA_CONCURRENCIA')", name="ejecuciones_rul_estado_check"),
        CheckConstraint("vigencia_horas BETWEEN 1 AND 168", name="ejecuciones_rul_vigencia_check"),
        CheckConstraint("total >= 0 AND estimadas >= 0 AND abstenciones >= 0 AND total = estimadas + abstenciones", name="ejecuciones_rul_totales_check"),
        CheckConstraint("(estado = 'EN_CURSO' AND finalizado_en IS NULL) OR (estado <> 'EN_CURSO' AND finalizado_en >= iniciado_en)", name="ejecuciones_rul_fechas_check"),
        CheckConstraint("(esperados IS NULL OR esperados >= 0) AND (procesados IS NULL OR procesados >= 0) AND (esperados IS NULL OR procesados IS NULL OR procesados <= esperados)", name="ejecuciones_rul_cobertura_check"),
        CheckConstraint("(limite_en IS NULL OR limite_en > iniciado_en) AND (latido_en IS NULL OR latido_en >= iniciado_en)", name="ejecuciones_rul_supervision_check"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    iniciado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(30))
    version_calculo: Mapped[str] = mapped_column(String(40))
    version_dataset: Mapped[str] = mapped_column(String(40))
    politica_alerta: Mapped[str] = mapped_column(String(40))
    dataset_sha256: Mapped[str | None] = mapped_column(String(64))
    modelo_sha256: Mapped[str | None] = mapped_column(String(64))
    entorno_modelo: Mapped[dict | None] = mapped_column(JSONB)
    limite_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    esperados: Mapped[int | None] = mapped_column(Integer)
    procesados: Mapped[int | None] = mapped_column(Integer)
    entorno: Mapped[dict] = mapped_column(JSONB)
    vigencia_horas: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer, default=0)
    estimadas: Mapped[int] = mapped_column(Integer, default=0)
    abstenciones: Mapped[int] = mapped_column(Integer, default=0)
    error_codigo: Mapped[str | None] = mapped_column(String(40))


class ResultadoRul(Base):
    __tablename__ = "resultados_rul"
    __table_args__ = (
        UniqueConstraint("ejecucion_id", "equipo_serie", name="resultados_rul_ejecucion_equipo_key"),
        CheckConstraint("origen IN ('LEGADO','BATCH')", name="resultados_rul_origen_check"),
        CheckConstraint("origen = 'LEGADO' OR (ejecucion_id IS NOT NULL AND fecha_evaluacion IS NOT NULL AND fecha_referencia IS NOT NULL AND tipo_referencia IS NOT NULL AND vence_en IS NOT NULL AND vence_en > calculado_en)", name="resultados_rul_entrada_check"),
        CheckConstraint("(dias_vida_util_remanente IS NOT NULL AND dias_vida_util_remanente >= 0 AND nivel_alerta IS NOT NULL AND nivel_alerta IN ('VERDE','AMARILLO','ROJO') AND motivo_no_estimable IS NULL) OR (dias_vida_util_remanente IS NULL AND nivel_alerta IS NULL AND motivo_no_estimable IS NOT NULL)", name="resultados_rul_valor_check"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ejecucion_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ejecuciones_rul.id"))
    equipo_serie: Mapped[str] = mapped_column(String(50), ForeignKey("equipos.serie"), index=True)
    origen: Mapped[str] = mapped_column(String(10))
    calculado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fecha_evaluacion: Mapped[date | None] = mapped_column(Date)
    fecha_referencia: Mapped[date | None] = mapped_column(Date)
    tipo_referencia: Mapped[str | None] = mapped_column(String(50))
    vence_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version_calculo: Mapped[str] = mapped_column(String(40))
    dias_vida_util_remanente: Mapped[int | None] = mapped_column(Integer)
    nivel_alerta: Mapped[str | None] = mapped_column(String(20))
    motivo_no_estimable: Mapped[str | None] = mapped_column(String(80))
