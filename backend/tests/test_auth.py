import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core import db as dbmod
from app.core.deps import require_role
from app.core.security import create_access_token
from app.models.usuario import Usuario


async def test_login_ok_devuelve_token(client, crear_usuario):
    await crear_usuario("GERENCIA", email="g@x.pe", password="pw-correcta")
    r = await client.post("/api/v1/auth/login", json={"email": "g@x.pe", "password": "pw-correcta"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"]


async def test_login_password_incorrecto_401(client, crear_usuario):
    await crear_usuario("GERENCIA", email="g@x.pe", password="pw-correcta")
    r = await client.post("/api/v1/auth/login", json={"email": "g@x.pe", "password": "mala"})
    assert r.status_code == 401


async def test_login_email_inexistente_401_mismo_mensaje(client, crear_usuario):
    await crear_usuario("GERENCIA", email="g@x.pe", password="pw-correcta")
    a = await client.post("/api/v1/auth/login", json={"email": "g@x.pe", "password": "mala"})
    b = await client.post("/api/v1/auth/login", json={"email": "nadie@x.pe", "password": "mala"})
    assert b.status_code == 401
    assert a.json() == b.json()


async def test_me_sin_token_401(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_me_devuelve_usuario_sin_password(client, crear_usuario, auth_headers):
    u = await crear_usuario("TECNICO", email="t@x.pe")
    r = await client.get("/api/v1/auth/me", headers=auth_headers(u))
    assert r.status_code == 200
    assert r.json()["email"] == "t@x.pe" and r.json()["rol"] == "TECNICO"
    assert "password_hash" not in r.json()


async def test_me_con_usuario_borrado_401(client, crear_usuario, auth_headers, db):
    u = await crear_usuario("TECNICO")
    headers = auth_headers(u)
    await db.delete(u)
    await db.flush()
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401


async def test_token_basura_401(client):
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer basura"})
    assert r.status_code == 401


async def test_require_role_tecnico_en_ruta_gerencia_403_y_gerencia_200(db, crear_usuario, auth_headers):
    mini = FastAPI()

    @mini.get("/solo-gerencia")
    async def solo(u: Usuario = Depends(require_role("GERENCIA"))):
        return {"ok": u.id}

    async def _s():
        yield db

    mini.dependency_overrides[dbmod.get_session] = _s
    t = await crear_usuario("TECNICO")
    g = await crear_usuario("GERENCIA")
    async with AsyncClient(transport=ASGITransport(app=mini), base_url="http://t") as c:
        assert (await c.get("/solo-gerencia", headers=auth_headers(t))).status_code == 403
        assert (await c.get("/solo-gerencia", headers=auth_headers(g))).status_code == 200
        assert (await c.get("/solo-gerencia")).status_code == 401


async def test_rol_invalido_no_se_puede_crear(db):
    db.add(Usuario(nombre="X", email="x@x.pe", password_hash="h", rol="ADMIN"))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_rol_del_token_no_otorga_privilegios_si_la_bd_dice_otra_cosa(db, crear_usuario):
    """El rol se lee de la BD, no del token: un token viejo de GERENCIA no sirve si ya es TECNICO."""
    mini = FastAPI()

    @mini.get("/solo-gerencia")
    async def solo(u: Usuario = Depends(require_role("GERENCIA"))):
        return {}

    async def _s():
        yield db

    mini.dependency_overrides[dbmod.get_session] = _s
    u = await crear_usuario("TECNICO")
    tok = create_access_token(u.id, "GERENCIA")  # token con rol inflado
    async with AsyncClient(transport=ASGITransport(app=mini), base_url="http://t") as c:
        r = await c.get("/solo-gerencia", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
