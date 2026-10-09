from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

TIPOS_SISTEMA = ("OSMOSIS_INVERSA", "ABLANDADOR", "FILTRO")


class Equipo(Base):
    __tablename__ = "equipos"
    __table_args__ = (
        CheckConstraint("tipo_sistema IN ('OSMOSIS_INVERSA','ABLANDADOR','FILTRO')", name="equipos_tipo_check"),
    )

    serie: Mapped[str] = mapped_column(String(50), primary_key=True)
    cliente_ruc: Mapped[str] = mapped_column(String(11), ForeignKey("clientes.ruc"), index=True)
    contrato_id: Mapped[int | None] = mapped_column(ForeignKey("contratos.id"))
    tipo_sistema: Mapped[str] = mapped_column(String(50))
    fecha_instalacion: Mapped[date] = mapped_column(Date)
    parametros_nominales: Mapped[dict] = mapped_column(JSONB)
    # Ultimo reemplazo/mantenimiento registrado por Gerencia (RN-01). El batch de RUL
    # (app/ml/batch_predicciones.py) cuenta los "dias en servicio" desde esta fecha en vez
    # de fecha_instalacion cuando esta presente, para que el reloj de vida util remanente
    # se pueda reiniciar sin tener que dar de baja y re-crear el equipo.
    fecha_ultima_mantencion: Mapped[date | None] = mapped_column(Date, nullable=True)
