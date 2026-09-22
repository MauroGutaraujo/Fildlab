from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings, normalize_async_url


def assert_distinct_test_database(database_url: str, database_url_test: str) -> None:
    """Salvaguarda para el fixture de tests: éste hace DROP SCHEMA public CASCADE contra
    DATABASE_URL_TEST. `DATABASE_URL` y `DATABASE_URL_TEST` conviven en el mismo `.env`;
    si por un copiar-pegar terminan siendo la misma URL, `pytest` borraría producción."""
    a, b = database_url.strip(), database_url_test.strip()
    if a and b and a == b:
        raise RuntimeError(
            "DATABASE_URL_TEST es la misma URL que DATABASE_URL. "
            "Los tests hacen DROP SCHEMA sobre DATABASE_URL_TEST: revisa backend/.env "
            "y apunta DATABASE_URL_TEST a una rama de Neon distinta antes de correr pytest."
        )


def make_engine(url: str) -> AsyncEngine:
    """Pool conservador: Koyeb (512 MB) + Neon serverless."""
    async_url, connect_args = normalize_async_url(url)
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
