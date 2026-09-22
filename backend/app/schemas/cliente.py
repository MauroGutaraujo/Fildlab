from pydantic import BaseModel, ConfigDict

from app.schemas.common import NonBlank, Ruc


class ClienteIn(BaseModel):
    ruc: Ruc
    razon_social: NonBlank
    direccion: NonBlank


class ClienteUpdate(BaseModel):
    razon_social: NonBlank
    direccion: NonBlank


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ruc: str
    razon_social: str
    direccion: str
    activo: bool
