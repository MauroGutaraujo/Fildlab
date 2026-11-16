"""Crea los usuarios iniciales (Gerencia y Técnico) en la base de datos.

Las contraseñas NO se guardan en el repositorio. Se leen de variables de entorno
o, si no están definidas, se piden por teclado sin mostrarlas:

    GERENCIA_PASSWORD=... TECNICO_PASSWORD=... python -m app.scripts.crear_usuarios_iniciales
    python -m app.scripts.crear_usuarios_iniciales "<cadena_neon>"

Si un usuario ya existe, no se modifica. Para cambiar una contraseña existente use
``python -m app.scripts.cambiar_password``.
"""

import asyncio
import getpass
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import normalize_async_url
from app.core.security import hash_password
from app.models.usuario import Usuario

MIN_PASSWORD = 12

USUARIOS_INICIALES = [
    {"nombre": "Administración Fildlab", "email": "gerencia@fildlab.pe", "rol": "GERENCIA", "env": "GERENCIA_PASSWORD"},
    {"nombre": "Técnico de Campo", "email": "tecnico@fildlab.pe", "rol": "TECNICO", "env": "TECNICO_PASSWORD"},
]


def obtener_password(variable: str, email: str) -> str:
    password = os.environ.get(variable) or getpass.getpass(f"Contraseña para {email}: ")
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"La contraseña de {email} debe tener al menos {MIN_PASSWORD} caracteres")
    return password


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
                continue
            nuevo = Usuario(
                nombre=u_data["nombre"],
                email=u_data["email"],
                password_hash=hash_password(obtener_password(u_data["env"], u_data["email"])),
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
