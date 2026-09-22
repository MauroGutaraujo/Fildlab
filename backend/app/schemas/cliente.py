from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.common import Ruc

# Topes iguales a las columnas de Postgres (clientes.razon_social VARCHAR(150));
# direccion es TEXT sin límite en la BD, pero se acota igual para un formulario sensato.
# Sin esto, un valor demasiado largo revienta el INSERT en Postgres y da 500 en vez de 422.
RazonSocial = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Direccion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ClienteIn(BaseModel):
    ruc: Ruc
    razon_social: RazonSocial
    direccion: Direccion


class ClienteUpdate(BaseModel):
    razon_social: RazonSocial
    direccion: Direccion


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ruc: str
    razon_social: str
    direccion: str
    activo: bool
