import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("JWT_SECRET", "test-secret-no-usar-en-produccion-0123456789")
_database_url_original = os.environ.get("DATABASE_URL", "")
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL_TEST", "")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core import db as dbmod  # noqa: E402
from app.core.db import assert_distinct_test_database  # noqa: E402

assert_distinct_test_database(_database_url_original, os.environ.get("DATABASE_URL_TEST", ""))
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
async def crear_cliente(db):
    from app.models.cliente import Cliente

    async def _crear(ruc="20612493821", razon_social="Clínica Test SAC", direccion="Trujillo"):
        c = Cliente(ruc=ruc, razon_social=razon_social, direccion=direccion)
        db.add(c)
        await db.flush()
        return c

    return _crear


@pytest_asyncio.fixture
async def crear_orden(db, crear_usuario, crear_cliente):
    """Órdenes las crea la PWA (Fase 3.2): en 3.1 se insertan por fixture (ruling D5)."""
    import uuid
    from datetime import date, datetime, timezone

    from app.models.contrato import Contrato
    from app.models.equipo import Equipo
    from app.models.orden import OrdenServicio

    async def _crear(estado="COMPROMETIDA", ruc="20612493821"):
        if await db.get(__import__("app.models.cliente", fromlist=["Cliente"]).Cliente, ruc) is None:
            await crear_cliente(ruc)
        tecnico = await crear_usuario("TECNICO")
        contrato = Contrato(cliente_ruc=ruc, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31),
                            monto_mensual_soles=1000)
        db.add(contrato)
        await db.flush()
        serie = f"SER-{uuid.uuid4().hex[:8]}"
        db.add(Equipo(serie=serie, cliente_ruc=ruc, contrato_id=contrato.id, tipo_sistema="OSMOSIS_INVERSA",
                      fecha_instalacion=date(2026, 1, 2), parametros_nominales={"presion_psi": 60}))
        await db.flush()
        o = OrdenServicio(id=uuid.uuid4(), contrato_id=contrato.id, equipo_serie=serie, tecnico_id=tecnico.id,
                          tipo_intervencion="PREVENTIVO", estado=estado,
                          fecha_creacion_cliente=datetime.now(timezone.utc))
        db.add(o)
        await db.flush()
        return o

    return _crear


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
