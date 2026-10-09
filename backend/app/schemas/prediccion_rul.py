from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

NivelAlerta = Literal["VERDE", "AMARILLO", "ROJO"]


class PrediccionRulOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipo_serie: str
    dias_vida_util_remanente: int
    nivel_alerta: NivelAlerta
    actualizado_en: datetime
