"""Crea el primer usuario GERENCIA.

Uso (variables de entorno, sin credenciales en el repo):
    GERENTE_NOMBRE=... GERENTE_EMAIL=... GERENTE_PASSWORD=... python -m app.scripts.crear_gerente
"""

import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.usuario import Usuario

MIN_PASSWORD = 12


async def asegurar_gerente(session: AsyncSession, nombre: str, email: str, password: str) -> Usuario:
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres")
    existente = (await session.execute(select(Usuario).where(Usuario.email == email))).scalar_one_or_none()
    if existente:
        return existente
    u = Usuario(nombre=nombre, email=email, password_hash=hash_password(password), rol="GERENCIA")
    session.add(u)
    await session.flush()
    return u


async def _main() -> None:
    from app.core.db import _get_sessionmaker

    async with _get_sessionmaker()() as session:
        u = await asegurar_gerente(
            session, os.environ["GERENTE_NOMBRE"], os.environ["GERENTE_EMAIL"], os.environ["GERENTE_PASSWORD"]
        )
        await session.commit()
        print(f"Gerente listo: {u.email} (id={u.id})")


if __name__ == "__main__":
    asyncio.run(_main())
