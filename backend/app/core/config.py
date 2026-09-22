from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_min: int = 60


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
