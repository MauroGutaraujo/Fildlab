from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Importar cada modelo aquí para que Base.metadata los conozca.
from app.models import cliente, componente, contrato, equipo, ejecucion_rul, orden, prediccion_rul, repuesto, usuario, venta  # noqa: E402,F401
