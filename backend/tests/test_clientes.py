import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

RUC = "20612493821"
BODY = {"ruc": RUC, "razon_social": "Clínica Norte S.A.C.", "direccion": "Av. España 100, Trujillo"}


async def test_crear_cliente_gerencia_201(client, gerente_h):
    r = await client.post("/api/v1/clientes", json=BODY, headers=gerente_h)
    assert r.status_code == 201
    assert r.json()["ruc"] == RUC and r.json()["activo"] is True


async def test_crear_cliente_tecnico_403(client, tecnico_h):  # RN-01
    assert (await client.post("/api/v1/clientes", json=BODY, headers=tecnico_h)).status_code == 403


async def test_crear_cliente_sin_token_401(client):
    assert (await client.post("/api/v1/clientes", json=BODY)).status_code == 401


@pytest.mark.parametrize("ruc", ["2061249382", "206124938211", "2061249382A", "20612 93821", " 20612493821", ""])
async def test_ruc_invalido_422(client, gerente_h, ruc):
    r = await client.post("/api/v1/clientes", json={**BODY, "ruc": ruc}, headers=gerente_h)
    assert r.status_code == 422


async def test_ruc_duplicado_409(client, gerente_h):
    await client.post("/api/v1/clientes", json=BODY, headers=gerente_h)
    r = await client.post("/api/v1/clientes", json=BODY, headers=gerente_h)
    assert r.status_code == 409


async def test_razon_social_muy_larga_422_nunca_500(client, gerente_h):
    """razon_social es VARCHAR(150); antes de la validación esto tumbaba la sesión con un 500 de Postgres."""
    r = await client.post("/api/v1/clientes", json={**BODY, "razon_social": "X" * 200}, headers=gerente_h)
    assert r.status_code == 422


async def test_direccion_muy_larga_422_nunca_500(client, gerente_h):
    r = await client.post("/api/v1/clientes", json={**BODY, "direccion": "Y" * 2000}, headers=gerente_h)
    assert r.status_code == 422


async def test_creacion_concurrente_con_mismo_ruc_una_gana_ninguna_500(engine):
    """Dos POST con el mismo RUC pueden pasar ambos el `get` previo bajo carrera real; ninguno debe dar 500.

    Usa el engine real (sin el `db` transaccional de los demás tests, que aislaría cada
    request en su propia sesión) para que cada request abra su propia sesión, como en producción.
    """
    import asyncio

    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.security import create_access_token, hash_password
    from app.main import app
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario

    ruc = "20988888801"
    async with AsyncSession(engine, expire_on_commit=False) as s:
        u = Usuario(nombre="Race", email="race@test.pe", password_hash=hash_password("x"), rol="GERENCIA")
        s.add(u)
        await s.commit()
        headers = {"Authorization": f"Bearer {create_access_token(u.id, u.rol)}"}

    async def crear():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            return await c.post("/api/v1/clientes", json={**BODY, "ruc": ruc}, headers=headers)

    try:
        r1, r2 = await asyncio.gather(crear(), crear())
        assert sorted([r1.status_code, r2.status_code]) == [201, 409]
    finally:
        async with AsyncSession(engine) as s:
            await s.execute(text("DELETE FROM clientes WHERE ruc = :r"), {"r": ruc})
            await s.execute(text("DELETE FROM usuarios WHERE email = 'race@test.pe'"))
            await s.commit()


@pytest.mark.parametrize("campo", ["razon_social", "direccion"])
async def test_campos_obligatorios_422(client, gerente_h, campo):
    for valor in (None, "", "   "):
        r = await client.post("/api/v1/clientes", json={**BODY, campo: valor}, headers=gerente_h)
        assert r.status_code == 422, (campo, valor)


async def test_tecnico_puede_listar_y_leer_200(client, gerente_h, tecnico_h):
    await client.post("/api/v1/clientes", json=BODY, headers=gerente_h)
    lista = await client.get("/api/v1/clientes", headers=tecnico_h)
    assert lista.status_code == 200 and [c["ruc"] for c in lista.json()] == [RUC]
    assert (await client.get(f"/api/v1/clientes/{RUC}", headers=tecnico_h)).status_code == 200


async def test_leer_sin_token_401(client):
    assert (await client.get("/api/v1/clientes")).status_code == 401


async def test_actualizar_solo_gerencia(client, gerente_h, tecnico_h):
    await client.post("/api/v1/clientes", json=BODY, headers=gerente_h)
    cambio = {"razon_social": "Nueva SAC", "direccion": "Otra 1"}
    assert (await client.put(f"/api/v1/clientes/{RUC}", json=cambio, headers=tecnico_h)).status_code == 403
    r = await client.put(f"/api/v1/clientes/{RUC}", json=cambio, headers=gerente_h)
    assert r.status_code == 200 and r.json()["razon_social"] == "Nueva SAC"


async def test_anular_es_baja_logica_y_solo_gerencia(client, gerente_h, tecnico_h):
    await client.post("/api/v1/clientes", json=BODY, headers=gerente_h)
    assert (await client.delete(f"/api/v1/clientes/{RUC}", headers=tecnico_h)).status_code == 403
    assert (await client.delete(f"/api/v1/clientes/{RUC}", headers=gerente_h)).status_code == 204
    r = await client.get(f"/api/v1/clientes/{RUC}", headers=gerente_h)
    assert r.status_code == 200 and r.json()["activo"] is False


async def test_cliente_inexistente_404(client, gerente_h):
    assert (await client.get("/api/v1/clientes/20000000001", headers=gerente_h)).status_code == 404
    r = await client.put("/api/v1/clientes/20000000001", json={"razon_social": "x", "direccion": "y"}, headers=gerente_h)
    assert r.status_code == 404
    assert (await client.delete("/api/v1/clientes/20000000001", headers=gerente_h)).status_code == 404


async def test_ruc_en_path_malformado_422_o_404_nunca_500(client, gerente_h):
    r = await client.get("/api/v1/clientes/abc", headers=gerente_h)
    assert r.status_code in (404, 422)


async def test_bd_rechaza_ruc_de_10_digitos(db):
    from app.models.cliente import Cliente

    db.add(Cliente(ruc="1234567890", razon_social="x", direccion="y"))
    with pytest.raises(IntegrityError):
        await db.flush()
