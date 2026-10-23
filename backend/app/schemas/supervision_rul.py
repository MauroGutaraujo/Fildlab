from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AvisoRul(BaseModel):
    codigo: str
    severidad: Literal["AVISO","INFO"]
    mensaje: str
    ejecucion_id: UUID | None = None


class SupervisionRulOut(BaseModel):
    consultado_en: datetime
    estado: Literal["NORMAL","ATENCION","SIN_EQUIPOS"]
    avisos: list[AvisoRul]
    ultima_exitosa_en: datetime | None
    total_equipos: int
    equipos_sin_evaluar: int
    ejecuciones_sin_cierre: int
