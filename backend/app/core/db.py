from collections.abc import AsyncIterator
from urllib.parse import unquote, urlsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings, normalize_async_url


def assert_distinct_test_database(database_url: str, database_url_test: str) -> None:
    """Reject ambiguous identities, including aliases and changed TLS/user options.

    Hostnames are not proof of isolation. Conservatively require different database
    names when both URLs are supplied; the test fixture also owns a private schema.
    """
    a, b = database_url.strip(), database_url_test.strip()
    if a and b and unquote(urlsplit(a).path) == unquote(urlsplit(b).path):
        raise RuntimeError(
            "DATABASE_URL_TEST puede ser la misma base que DATABASE_URL. "
            "Use una instancia local desechable y un nombre de base distinto."
        )


def assert_safe_test_target(url: str) -> None:
    """Tests accept only explicit loopback PostgreSQL databases named for tests."""
    parts = urlsplit(url)
    name = unquote(parts.path).lstrip("/")
    if (parts.scheme not in {"postgresql", "postgres", "postgresql+asyncpg"}
            or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
            or not (name.startswith("test_") or name.endswith("_test"))
            or parts.query or parts.fragment):
        raise RuntimeError("DATABASE_URL_TEST requiere PostgreSQL local desechable, base test_* o *_test y sin query")


def make_engine(url: str, *, schema: str | None = None) -> AsyncEngine:
    """Pool conservador: Koyeb (512 MB) + Neon serverless."""
    async_url, connect_args = normalize_async_url(url)
    if schema is not None:
        import re

        if re.fullmatch(r"test_[0-9a-f]{32}", schema) is None:
            raise ValueError("Esquema de pruebas inválido")
        connect_args["server_settings"] = {"search_path": schema}
    return create_async_engine(
        async_url,
        pool_size=2,
        max_overflow=1,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args,
    )


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _engine, _sessionmaker
    if _sessionmaker is None:
        _engine = make_engine(get_settings().database_url)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
