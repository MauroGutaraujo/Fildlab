from sqlalchemy import text

from app.core.config import normalize_async_url
from app.core.db import make_engine


def test_pool_conservador():
    eng = make_engine("postgresql://u:p@host/db?sslmode=require")
    assert eng.pool.size() == 2
    assert eng.pool._max_overflow == 1
    assert eng.pool._pre_ping is True
    assert eng.pool._recycle == 300


def test_normalize_url_para_asyncpg_y_pooler_de_neon():
    url, args = normalize_async_url("postgresql://u:p@ep-x-pooler.aws.neon.tech/db?sslmode=require")
    assert url == "postgresql+asyncpg://u:p@ep-x-pooler.aws.neon.tech/db"
    assert args["ssl"] is True
    assert args["statement_cache_size"] == 0


async def test_conexion_neon_responde(db):
    assert (await db.execute(text("SELECT 1"))).scalar() == 1
