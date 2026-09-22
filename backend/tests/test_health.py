from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_healthz_devuelve_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_healthz_no_requiere_bd(monkeypatch):
    # Si healthz tocara la BD, esta dependencia reventaría.
    from app.core import db

    async def boom():
        raise RuntimeError("healthz no debe abrir sesión")
        yield  # pragma: no cover

    app.dependency_overrides[db.get_session] = boom
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/v1/healthz")
        assert r.status_code == 200
    finally:
        app.dependency_overrides.clear()
