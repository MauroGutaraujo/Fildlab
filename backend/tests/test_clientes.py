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
