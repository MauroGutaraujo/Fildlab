from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Importar cada modelo aquí para que Base.metadata los conozca.
from app.models import cliente, contrato, usuario  # noqa: E402,F401
