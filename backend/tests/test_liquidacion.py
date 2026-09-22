import uuid

import pytest
from sqlalchemy import func, select

from app.models.orden import ActaInmutable, AdendaCorreccion
from app.models.repuesto import MovimientoInventario


@pytest.fixture
async def acta(db, crear_orden):
    orden = await crear_orden()
    a = ActaInmutable(orden_id=orden.id, payload_raw='{"consumibles":[{"FILT-05":2}]}', hash_sha256="a" * 64,
                      previous_hash=None, firma_base64="AAAA", gps_latitud=-8.1116, gps_longitud=-79.0288)
    db.add(a)
    await db.flush()
    return orden, a


async def _con_stock(client, h, codigo="FILT-05", stock=10):
    await client.post("/api/v1/repuestos", json={"codigo": codigo, "descripcion": codigo, "costo_unitario_soles": "5"}, headers=h)
    await client.post("/api/v1/inventario/movimientos", json={"repuesto_codigo": codigo, "tipo": "ENTRADA", "cantidad": stock}, headers=h)


async def test_listar_y_leer_ordenes_con_filtro_de_estado(client, gerente_h, tecnico_h, crear_orden):
    a = await crear_orden(estado="COMPROMETIDA")
    b = await crear_orden(estado="LIQUIDADA")
    todas = await client.get("/api/v1/ordenes", headers=tecnico_h)
    assert {o["id"] for o in todas.json()} == {str(a.id), str(b.id)}
    solo = await client.get("/api/v1/ordenes?estado=COMPROMETIDA", headers=tecnico_h)
    assert [o["id"] for o in solo.json()] == [str(a.id)]
    assert (await client.get(f"/api/v1/ordenes/{a.id}", headers=tecnico_h)).status_code == 200
    assert (await client.get("/api/v1/ordenes?estado=INVENTADO", headers=gerente_h)).status_code == 422


async def test_orden_inexistente_404_y_uuid_malformado_422(client, gerente_h):
    assert (await client.get(f"/api/v1/ordenes/{uuid.uuid4()}", headers=gerente_h)).status_code == 404
    assert (await client.get("/api/v1/ordenes/no-es-uuid", headers=gerente_h)).status_code == 422
    assert (await client.post(f"/api/v1/ordenes/{uuid.uuid4()}/liquidar", headers=gerente_h)).status_code == 404


async def test_liquidar_orden_comprometida_pasa_a_liquidada(client, gerente_h, crear_orden):
    o = await crear_orden(estado="COMPROMETIDA")
    r = await client.post(f"/api/v1/ordenes/{o.id}/liquidar", headers=gerente_h)
    assert r.status_code == 200 and r.json()["estado"] == "LIQUIDADA"
    assert (await client.get(f"/api/v1/ordenes/{o.id}", headers=gerente_h)).json()["estado"] == "LIQUIDADA"


async def test_liquidar_orden_sincronizada_tambien_se_puede(client, gerente_h, crear_orden):
    o = await crear_orden(estado="SINCRONIZADA")
    assert (await client.post(f"/api/v1/ordenes/{o.id}/liquidar", headers=gerente_h)).status_code == 200


async def test_liquidar_dos_veces_409(client, gerente_h, crear_orden):
    o = await crear_orden(estado="COMPROMETIDA")
    await client.post(f"/api/v1/ordenes/{o.id}/liquidar", headers=gerente_h)
    assert (await client.post(f"/api/v1/ordenes/{o.id}/liquidar", headers=gerente_h)).status_code == 409


async def test_liquidar_solo_gerencia(client, tecnico_h, crear_orden):
    o = await crear_orden(estado="COMPROMETIDA")
    assert (await client.post(f"/api/v1/ordenes/{o.id}/liquidar", headers=tecnico_h)).status_code == 403
    assert (await client.get(f"/api/v1/ordenes/{o.id}", headers=tecnico_h)).json()["estado"] == "COMPROMETIDA"


async def test_liquidar_no_modifica_acta_inmutable(client, gerente_h, acta, db):
    orden, a = acta
    antes = (a.payload_raw, a.hash_sha256, a.previous_hash, a.firma_base64)
    await client.post(f"/api/v1/ordenes/{orden.id}/liquidar", headers=gerente_h)
    await db.refresh(a)
    assert (a.payload_raw, a.hash_sha256, a.previous_hash, a.firma_base64) == antes


async def test_crear_adenda_vincula_orden_y_gerente(client, crear_usuario, auth_headers, acta, db):
    g = await crear_usuario("GERENCIA")
    orden, _ = acta
    r = await client.post(f"/api/v1/ordenes/{orden.id}/adendas", json={"observacion": "Se consumieron 3, no 2"},
                          headers=auth_headers(g))
    assert r.status_code == 201
    b = r.json()
    assert b["orden_id"] == str(orden.id) and b["gerente_id"] == g.id and b["fecha_adenda"]
    lista = await client.get(f"/api/v1/ordenes/{orden.id}/adendas", headers=auth_headers(g))
    assert [x["id"] for x in lista.json()] == [b["id"]]


async def test_adenda_no_edita_el_acta(client, gerente_h, acta, db):
    orden, a = acta
    antes = (a.payload_raw, a.hash_sha256, a.firma_base64)
    await client.post(f"/api/v1/ordenes/{orden.id}/adendas", json={"observacion": "corrección"}, headers=gerente_h)
    await db.refresh(a)
    assert (a.payload_raw, a.hash_sha256, a.firma_base64) == antes
    assert (await db.execute(select(func.count()).select_from(ActaInmutable))).scalar() == 1


async def test_adenda_tambien_sobre_orden_ya_liquidada(client, gerente_h, crear_orden):
    o = await crear_orden(estado="LIQUIDADA")
    r = await client.post(f"/api/v1/ordenes/{o.id}/adendas", json={"observacion": "ajuste posterior"}, headers=gerente_h)
    assert r.status_code == 201


@pytest.mark.parametrize("obs", ["", "   ", None])
async def test_adenda_sin_observacion_422(client, gerente_h, crear_orden, obs):
    o = await crear_orden()
    r = await client.post(f"/api/v1/ordenes/{o.id}/adendas", json={"observacion": obs}, headers=gerente_h)
    assert r.status_code == 422


async def test_adenda_solo_gerencia_y_orden_inexistente_404(client, gerente_h, tecnico_h, crear_orden):
    o = await crear_orden()
    assert (await client.post(f"/api/v1/ordenes/{o.id}/adendas", json={"observacion": "x"}, headers=tecnico_h)).status_code == 403
    assert (await client.post(f"/api/v1/ordenes/{uuid.uuid4()}/adendas", json={"observacion": "x"}, headers=gerente_h)).status_code == 404


async def test_adenda_con_ajuste_repuestos_genera_movimientos_de_ajuste(client, gerente_h, crear_orden, db):
    o = await crear_orden()
    await _con_stock(client, gerente_h, "FILT-05", 10)
    body = {"observacion": "Se usaron 3 filtros, no 2", "ajuste_repuestos": [{"repuesto_codigo": "FILT-05", "delta": -1}]}
    r = await client.post(f"/api/v1/ordenes/{o.id}/adendas", json=body, headers=gerente_h)
    assert r.status_code == 201
    stock = (await client.get("/api/v1/repuestos/FILT-05", headers=gerente_h)).json()["stock_almacen_central"]
    assert stock == 9
    m = (await db.execute(select(MovimientoInventario).where(MovimientoInventario.orden_id == o.id))).scalars().all()
    assert [(x.tipo, x.cantidad) for x in m] == [("AJUSTE_SALIDA", 1)]
    # delta positivo devuelve stock
    body2 = {"observacion": "Se devolvieron 2", "ajuste_repuestos": [{"repuesto_codigo": "FILT-05", "delta": 2}]}
    await client.post(f"/api/v1/ordenes/{o.id}/adendas", json=body2, headers=gerente_h)
    assert (await client.get("/api/v1/repuestos/FILT-05", headers=gerente_h)).json()["stock_almacen_central"] == 11


async def test_adenda_ajuste_excede_stock_409_sin_adenda(client, gerente_h, crear_orden, db):
    o = await crear_orden()
    await _con_stock(client, gerente_h, "FILT-05", 2)
    body = {"observacion": "x", "ajuste_repuestos": [{"repuesto_codigo": "FILT-05", "delta": -5}]}
    assert (await client.post(f"/api/v1/ordenes/{o.id}/adendas", json=body, headers=gerente_h)).status_code == 409
    assert (await db.execute(select(func.count()).select_from(AdendaCorreccion))).scalar() == 0
    assert (await client.get("/api/v1/repuestos/FILT-05", headers=gerente_h)).json()["stock_almacen_central"] == 2


async def test_adenda_ajuste_repuesto_inexistente_404_o_delta_cero_422(client, gerente_h, crear_orden, db):
    o = await crear_orden()
    r = await client.post(f"/api/v1/ordenes/{o.id}/adendas", headers=gerente_h,
                          json={"observacion": "x", "ajuste_repuestos": [{"repuesto_codigo": "NOPE", "delta": 1}]})
    assert r.status_code == 404
    r = await client.post(f"/api/v1/ordenes/{o.id}/adendas", headers=gerente_h,
                          json={"observacion": "x", "ajuste_repuestos": [{"repuesto_codigo": "NOPE", "delta": 0}]})
    assert r.status_code == 422
    assert (await db.execute(select(func.count()).select_from(AdendaCorreccion))).scalar() == 0


async def test_no_existen_endpoints_para_editar_o_borrar_ordenes_ni_actas(client, gerente_h, acta):
    orden, _ = acta
    assert (await client.put(f"/api/v1/ordenes/{orden.id}", json={}, headers=gerente_h)).status_code == 405
    assert (await client.patch(f"/api/v1/ordenes/{orden.id}", json={}, headers=gerente_h)).status_code == 405
    assert (await client.delete(f"/api/v1/ordenes/{orden.id}", headers=gerente_h)).status_code == 405
    assert (await client.put(f"/api/v1/ordenes/{orden.id}/acta", json={}, headers=gerente_h)).status_code == 404
    assert (await client.delete(f"/api/v1/ordenes/{orden.id}/acta", headers=gerente_h)).status_code == 404


async def test_sin_token_401(client):
    assert (await client.get("/api/v1/ordenes")).status_code == 401
