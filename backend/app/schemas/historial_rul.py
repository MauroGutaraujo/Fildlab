from datetime import date, datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EjecucionRulOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    iniciado_en: datetime
    finalizado_en: datetime | None
    estado: Literal["EN_CURSO", "COMPLETADA", "FALLIDA", "OMITIDA_CONCURRENCIA"]
    version_calculo: str
    version_dataset: str
    politica_alerta: str
    dataset_sha256: str | None
    modelo_sha256: str | None
    entorno_modelo: dict[str,str] | None
    limite_en: datetime | None
    latido_en: datetime | None
    esperados: int | None
    procesados: int | None
    entorno: dict[str, str]
    vigencia_horas: int
    total: int
    estimadas: int
    abstenciones: int
    error_codigo: str | None


class ResultadoHistoricoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ejecucion_id: UUID | None
    equipo_serie: str
    origen: Literal["LEGADO", "BATCH"]
    uso: Literal["HISTORICO_NO_VIGENTE"] = "HISTORICO_NO_VIGENTE"
    calculado_en: datetime
    fecha_evaluacion: date | None
    fecha_referencia: date | None
    tipo_referencia: str | None
    vence_en: datetime | None
    version_calculo: str
    version_dataset: str | None = None
    politica_alerta: str | None = None
    dataset_sha256: str | None = None
    modelo_sha256: str | None = None
    dias_vida_util_remanente: int | None
    nivel_alerta: str | None
    motivo_no_estimable: str | None


T = TypeVar("T")


class PaginaRul(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
