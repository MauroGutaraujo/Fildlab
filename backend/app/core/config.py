from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_min: int = 60
    cors_origins: list[str] = [
        "https://fildlab.pages.dev", "https://fildlab-pwa.pages.dev",
        "http://localhost:5173", "http://localhost:5174",
    ]
    max_request_body_bytes: int = Field(default=2 * 1024 * 1024, ge=1024, le=16 * 1024 * 1024)
    request_body_timeout_seconds: float = Field(default=15, gt=0, le=120)
    login_attempts_per_window: int = Field(default=10, ge=1, le=1000)
    login_global_attempts_per_window: int = Field(default=60, ge=1, le=10000)
    login_window_seconds: int = Field(default=60, ge=1, le=3600)
    password_verify_concurrency: int = Field(default=2, ge=1, le=8)

    @field_validator("cors_origins")
    @classmethod
    def _explicit_origins(cls, values: list[str]) -> list[str]:
        for value in values:
            parts = urlsplit(value)
            if (parts.scheme not in {"http", "https"} or not parts.hostname
                    or "*" in value or parts.path or parts.query or parts.fragment
                    or parts.username or parts.password):
                raise ValueError("CORS_ORIGINS debe contener orígenes HTTP(S) explícitos sin ruta")
        return values

    @field_validator("database_url")
    @classmethod
    def _database_url_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("DATABASE_URL es obligatoria")
        return v

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_suficiente(cls, v: str) -> str:
        # Un secreto vacío o corto deja el firmado de JWT trivial de falsificar (RNF-06).
        if len(v) < MIN_JWT_SECRET:
            raise ValueError(f"JWT_SECRET debe tener al menos {MIN_JWT_SECRET} caracteres")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


def normalize_async_url(url: str) -> tuple[str, dict]:
    """Adapta una URL de Neon (libpq) a asyncpg.

    asyncpg no entiende `sslmode`, y el pooler de Neon (pgbouncer) exige
    desactivar la caché de sentencias preparadas.
    """
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    scheme = "postgresql+asyncpg"
    new = urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    args: dict = {"statement_cache_size": 0}
    if sslmode in ("require", "verify-ca", "verify-full"):
        args["ssl"] = True
    return new, args
