from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

import conftest as fixtures


async def test_fixture_setup_failure_cleans_only_owned_schema(engine, monkeypatch):
    owned = uuid4()
    sibling = f"test_{uuid4().hex}"
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{sibling}"'))
        await conn.execute(text(f'CREATE TABLE "{sibling}".sentinel (id integer)'))
        await conn.execute(text(f'INSERT INTO "{sibling}".sentinel VALUES (73)'))
    monkeypatch.setattr(fixtures, "uuid4", lambda: owned)

    def failing_setup(connection):
        raise RuntimeError("injected model setup failure")

    monkeypatch.setattr(fixtures.Base.metadata, "create_all", failing_setup)
    try:
        generator = fixtures.engine.__wrapped__()
        with pytest.raises(RuntimeError, match="injected"):
            await anext(generator)
        async with engine.connect() as conn:
            assert await conn.scalar(text("SELECT to_regnamespace(:name)"), {"name": f"test_{owned.hex}"}) is None
            assert await conn.scalar(text(f'SELECT id FROM "{sibling}".sentinel')) == 73
            assert await conn.scalar(text("SELECT to_regnamespace('public')")) is not None
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{sibling}" CASCADE'))


async def test_fixture_collision_never_drops_schema_it_did_not_create(engine, monkeypatch):
    existing = uuid4()
    name = f"test_{existing.hex}"
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{name}"'))
        await conn.execute(text(f'CREATE TABLE "{name}".sentinel (id integer)'))
        await conn.execute(text(f'INSERT INTO "{name}".sentinel VALUES (81)'))
    monkeypatch.setattr(fixtures, "uuid4", lambda: existing)
    try:
        generator = fixtures.engine.__wrapped__()
        with pytest.raises(ProgrammingError):
            await anext(generator)
        async with engine.connect() as conn:
            assert await conn.scalar(text(f'SELECT id FROM "{name}".sentinel')) == 81
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{name}" CASCADE'))


async def test_engine_uses_private_schema_without_public_fallback(engine):
    async with engine.connect() as conn:
        schema = await conn.scalar(text("SELECT current_schema()"))
        assert schema.startswith("test_")
        assert await conn.scalar(text("SHOW search_path")) == schema
        assert await conn.scalar(text("SELECT table_schema FROM information_schema.tables WHERE table_name='usuarios' AND table_schema=current_schema()")) == schema
