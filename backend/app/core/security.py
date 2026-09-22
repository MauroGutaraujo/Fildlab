from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

# Parámetros OWASP: m=19 MiB, t=2, p=1
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


class TokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenPayload:
    sub: int
    rol: str


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(sub: int, rol: str, expires_delta: timedelta | None = None) -> str:
    s = get_settings()
    exp = datetime.now(UTC) + (expires_delta if expires_delta is not None else timedelta(minutes=s.jwt_expire_min))
    return jwt.encode({"sub": str(sub), "rol": rol, "exp": exp}, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    s = get_settings()
    try:
        data = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], options={"require": ["exp", "sub"]})
        return TokenPayload(sub=int(data["sub"]), rol=str(data.get("rol", "")))
    except (jwt.PyJWTError, ValueError) as e:
        raise TokenError(str(e)) from e
