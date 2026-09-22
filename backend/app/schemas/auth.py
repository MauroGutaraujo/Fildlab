from typing import Literal

from pydantic import BaseModel, ConfigDict


class LoginIn(BaseModel):
    email: str
    password: str
    # "turno": sesion extendida de 12h para tecnicos de campo sin senal (3.2).
    duracion: Literal["normal", "turno"] = "normal"


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol: str
