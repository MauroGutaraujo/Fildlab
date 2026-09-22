import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("JWT_SECRET", "test-secret-no-usar-en-produccion-0123456789")
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL_TEST", "")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core import db as dbmod  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def engine():
    if not os.environ.get("DATABASE_URL_TEST"):
        pytest.skip("DATABASE_URL_TEST no configurada")
    eng = dbmod.make_engine(os.environ["DATABASE_URL_TEST"])
    async with eng.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """Sesión aislada: todo lo que haga el test se revierte al terminar."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        yield session
        await session.close()
        await trans.rollback()


@pytest_asyncio.fixture
async def crear_usuario(db):
    from itertools import count

    from app.core.security import hash_password
    from app.models.usuario import Usuario

    n = count(1)

    async def _crear(rol="GERENCIA", email=None, password="pw-de-prueba", nombre="Usuario Test"):
        u = Usuario(
            nombre=nombre,
            email=email or f"u{next(n)}-{rol.lower()}@test.pe",
            password_hash=hash_password(password),
            rol=rol,
        )
        db.add(u)
        await db.flush()
        return u

    return _crear


@pytest.fixture
def auth_headers():
    from app.core.security import create_access_token

    def _h(usuario):
        return {"Authorization": f"Bearer {create_access_token(usuario.id, usuario.rol)}"}

    return _h


@pytest_asyncio.fixture
async def gerente_h(crear_usuario, auth_headers):
    return auth_headers(await crear_usuario("GERENCIA"))


@pytest_asyncio.fixture
async def tecnico_h(crear_usuario, auth_headers):
    return auth_headers(await crear_usuario("TECNICO"))


@pytest_asyncio.fixture
async def client(db):
    async def _override():
        yield db

    app.dependency_overrides[dbmod.get_session] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()
