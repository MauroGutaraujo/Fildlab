from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.usuario import Usuario
from app.schemas.auth import LoginIn, TokenOut, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash de relleno: verificamos siempre para no filtrar por tiempo si el email existe.
_DUMMY_HASH = hash_password("relleno-anti-enumeracion")


@router.post("/login", response_model=TokenOut)
async def login(datos: LoginIn, session: AsyncSession = Depends(get_session)) -> TokenOut:
    usuario = (await session.execute(select(Usuario).where(Usuario.email == datos.email))).scalar_one_or_none()
    ok = verify_password(datos.password, usuario.password_hash if usuario else _DUMMY_HASH)
    if usuario is None or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    return TokenOut(access_token=create_access_token(usuario.id, usuario.rol))


@router.get("/me", response_model=UsuarioOut)
async def me(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    return usuario
