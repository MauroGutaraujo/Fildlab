import pytest
from sqlalchemy import func, select

from app.models.contrato import Contrato

BODY = {
    "cliente_ruc": "20612493821",
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-12-31",
    "monto_mensual_soles": "1500.00",
    "sla_horas_max_respuesta": 6,
}


@pytest.fixture
async def cliente(crear_cliente):
    return await crear_cliente("20612493821")


async def test_crear_contrato_gerencia_201(client, gerente_h, cliente):
    r = await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)
    assert r.status_code == 201
    b = r.json()
    assert b["estado"] == "ACTIVO" and b["sla_horas_max_respuesta"] == 6 and b["monto_mensual_soles"] == "1500.00"


async def test_crear_contrato_tecnico_403(client, tecnico_h, cliente):  # RN-01
    assert (await client.post("/api/v1/contratos", json=BODY, headers=tecnico_h)).status_code == 403


async def test_sla_por_defecto_4(client, gerente_h, cliente):
    body = {k: v for k, v in BODY.items() if k != "sla_horas_max_respuesta"}
    r = await client.post("/api/v1/contratos", json=body, headers=gerente_h)
    assert r.status_code == 201 and r.json()["sla_horas_max_respuesta"] == 4


async def test_fecha_fin_anterior_a_inicio_422(client, gerente_h, cliente):
    r = await client.post("/api/v1/contratos", json={**BODY, "fecha_fin": "2025-12-31"}, headers=gerente_h)
    assert r.status_code == 422


@pytest.mark.parametrize("monto", ["0", "-10", "0.00", "abc", "100000000.00"])
async def test_monto_invalido_422(client, gerente_h, cliente, monto):
    r = await client.post("/api/v1/contratos", json={**BODY, "monto_mensual_soles": monto}, headers=gerente_h)
    assert r.status_code == 422


@pytest.mark.parametrize("sla", [0, -1, 1.5, "x"])
async def test_sla_invalido_422(client, gerente_h, cliente, sla):
    r = await client.post("/api/v1/contratos", json={**BODY, "sla_horas_max_respuesta": sla}, headers=gerente_h)
    assert r.status_code == 422


async def test_cliente_inexistente_404(client, gerente_h):
    r = await client.post("/api/v1/contratos", json={**BODY, "cliente_ruc": "20999999999"}, headers=gerente_h)
    assert r.status_code == 404


async def test_cliente_anulado_409(client, gerente_h, cliente):
    await client.delete("/api/v1/clientes/20612493821", headers=gerente_h)
    r = await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)
    assert r.status_code == 409


async def test_contrato_incompleto_bloqueado_sin_fila_parcial(client, gerente_h, cliente, db):
    for campo in ("cliente_ruc", "fecha_inicio", "fecha_fin", "monto_mensual_soles"):
        r = await client.post("/api/v1/contratos", json={k: v for k, v in BODY.items() if k != campo}, headers=gerente_h)
        assert r.status_code == 422, campo
    assert (await db.execute(select(func.count()).select_from(Contrato))).scalar() == 0


async def test_fecha_invalida_422(client, gerente_h, cliente):
    r = await client.post("/api/v1/contratos", json={**BODY, "fecha_inicio": "2026-02-30"}, headers=gerente_h)
    assert r.status_code == 422


async def test_tecnico_lee_y_lista_200(client, gerente_h, tecnico_h, cliente):
    c = (await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)).json()
    assert (await client.get(f"/api/v1/contratos/{c['id']}", headers=tecnico_h)).status_code == 200
    lista = await client.get("/api/v1/contratos", headers=tecnico_h)
    assert [x["id"] for x in lista.json()] == [c["id"]]
    filtrada = await client.get("/api/v1/contratos?cliente_ruc=20000000001", headers=tecnico_h)
    assert filtrada.json() == []


async def test_contrato_inexistente_404(client, gerente_h):
    assert (await client.get("/api/v1/contratos/999999", headers=gerente_h)).status_code == 404
    assert (await client.post("/api/v1/contratos/999999/anular", headers=gerente_h)).status_code == 404


async def test_actualizar_contrato_solo_gerencia_y_valida(client, gerente_h, tecnico_h, cliente):
    c = (await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)).json()
    cambio = {"fecha_inicio": "2026-02-01", "fecha_fin": "2027-01-31", "monto_mensual_soles": "1800.50",
              "sla_horas_max_respuesta": 2}
    assert (await client.put(f"/api/v1/contratos/{c['id']}", json=cambio, headers=tecnico_h)).status_code == 403
    r = await client.put(f"/api/v1/contratos/{c['id']}", json=cambio, headers=gerente_h)
    assert r.status_code == 200 and r.json()["sla_horas_max_respuesta"] == 2
    malo = await client.put(f"/api/v1/contratos/{c['id']}", json={**cambio, "fecha_fin": "2020-01-01"}, headers=gerente_h)
    assert malo.status_code == 422


async def test_anular_contrato_cambia_estado_solo_gerencia_y_no_se_repite(client, gerente_h, tecnico_h, cliente):
    c = (await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)).json()
    assert (await client.post(f"/api/v1/contratos/{c['id']}/anular", headers=tecnico_h)).status_code == 403
    r = await client.post(f"/api/v1/contratos/{c['id']}/anular", headers=gerente_h)
    assert r.status_code == 200 and r.json()["estado"] == "ANULADO"
    assert (await client.post(f"/api/v1/contratos/{c['id']}/anular", headers=gerente_h)).status_code == 409


async def test_no_se_edita_contrato_anulado_409(client, gerente_h, cliente):
    c = (await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)).json()
    await client.post(f"/api/v1/contratos/{c['id']}/anular", headers=gerente_h)
    cambio = {k: BODY[k] for k in ("fecha_inicio", "fecha_fin", "monto_mensual_soles", "sla_horas_max_respuesta")}
    assert (await client.put(f"/api/v1/contratos/{c['id']}", json=cambio, headers=gerente_h)).status_code == 409


async def test_anular_cliente_con_contrato_activo_409(client, gerente_h, cliente):
    c = (await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)).json()
    assert (await client.delete("/api/v1/clientes/20612493821", headers=gerente_h)).status_code == 409
    await client.post(f"/api/v1/contratos/{c['id']}/anular", headers=gerente_h)
    assert (await client.delete("/api/v1/clientes/20612493821", headers=gerente_h)).status_code == 204


async def test_contratos_solapados_del_mismo_cliente_se_permiten(client, gerente_h, cliente):
    # Ruling ledgerizado: un cliente puede tener varios contratos (p. ej. por equipo) con vigencias que coinciden.
    assert (await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)).status_code == 201
    assert (await client.post("/api/v1/contratos", json=BODY, headers=gerente_h)).status_code == 201
