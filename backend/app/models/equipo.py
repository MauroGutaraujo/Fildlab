from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, String
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
    # Antecedente legado sin componente/evidencia: se conserva, pero no reinicia RUL.
    fecha_ultima_mantencion: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Cabeza serializada bajo el lock del equipo; now() no representa orden de commits.
    ultimo_hash_acta: Mapped[str | None] = mapped_column(String(64))
    secuencia_acta: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", default=0)
