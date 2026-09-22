from sqlalchemy import Boolean, CheckConstraint, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (CheckConstraint("LENGTH(ruc) = 11", name="clientes_ruc_len_check"),)

    ruc: Mapped[str] = mapped_column(String(11), primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(150))
    direccion: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true(), default=True)
