from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import TokenError, decode_access_token
from app.models.usuario import Usuario

_bearer = HTTPBearer(auto_error=False)


def _no_autenticado() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado", headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> Usuario:
    if cred is None:
        raise _no_autenticado()
    try:
        payload = decode_access_token(cred.credentials)
    except TokenError:
        raise _no_autenticado() from None
    usuario = await session.get(Usuario, payload.sub)
    if usuario is None:
        raise _no_autenticado()
    return usuario  # el rol vigente es el de la BD, no el del token


def require_role(*roles: str) -> Callable[..., Usuario]:
    async def _dep(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permisos insuficientes")
        return usuario

    return _dep
