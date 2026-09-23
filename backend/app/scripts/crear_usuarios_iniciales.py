"""Script para crear los usuarios iniciales (Gerencia y Técnico) en la base de datos de producción.

Uso:
    python -m app.scripts.crear_usuarios_iniciales "<cadena_neon>"
o simplemente:
    python -m app.scripts.crear_usuarios_iniciales
(si DATABASE_URL está definida en .env o en el entorno)
"""

import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import normalize_async_url
from app.core.security import hash_password
from app.models.usuario import Usuario

USUARIOS_INICIALES = [
    {
        "nombre": "Administración Fildlab",
        "email": "gerencia@fildlab.pe",
        "password": "Fildlab2026Gerente!",
        "rol": "GERENCIA",
    },
    {
        "nombre": "Técnico de Campo",
        "email": "tecnico@fildlab.pe",
        "password": "Fildlab2026Tecnico!",
        "rol": "TECNICO",
    },
]


async def crear_usuarios(db_url: str) -> None:
    async_url, connect_args = normalize_async_url(db_url)
    engine = create_async_engine(async_url, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        for u_data in USUARIOS_INICIALES:
            existente = (
                await session.execute(select(Usuario).where(Usuario.email == u_data["email"]))
            ).scalar_one_or_none()

            if existente:
                print(f"[-] Usuario ya existe: {u_data['email']} (Rol: {existente.rol})")
            else:
                nuevo = Usuario(
                    nombre=u_data["nombre"],
                    email=u_data["email"],
                    password_hash=hash_password(u_data["password"]),
                    rol=u_data["rol"],
                )
                session.add(nuevo)
                await session.commit()
                print(f"[+] Creado exitosamente: {u_data['email']} (Rol: {u_data['rol']})")

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        from app.core.config import get_settings
        url = get_settings().database_url

    asyncio.run(crear_usuarios(url))
