"""Cambia la contraseña de un usuario existente sin dejarla escrita en ningún archivo.

Uso (la contraseña se pide por teclado y no se muestra):
    python -m app.scripts.cambiar_password gerencia@fildlab.pe

Necesita DATABASE_URL en el entorno o en backend/.env (en Render ya está definida).
"""

import asyncio
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.usuario import Usuario

MIN_PASSWORD = 12


async def cambiar_password(session: AsyncSession, email: str, nueva: str) -> Usuario:
    if len(nueva) < MIN_PASSWORD:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres")
    usuario = (await session.execute(select(Usuario).where(Usuario.email == email))).scalar_one_or_none()
    if usuario is None:
        raise LookupError(f"No existe un usuario con el correo {email}")
    usuario.password_hash = hash_password(nueva)
    await session.flush()
    return usuario


async def _main(email: str) -> None:
    from app.core.db import _get_sessionmaker

    nueva = getpass.getpass(f"Nueva contraseña para {email}: ")
    if nueva != getpass.getpass("Repita la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden; no se cambió nada.")
    async with _get_sessionmaker()() as session:
        u = await cambiar_password(session, email, nueva)
        await session.commit()
        print(f"Contraseña actualizada: {u.email} (rol {u.rol})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python -m app.scripts.cambiar_password <correo>")
    asyncio.run(_main(sys.argv[1]))
