import uuid
from datetime import datetime, timezone

import pytest
from orden_helpers import firma_png

LECTURAS = dict(tds_entrada_ppm=350, tds_post_membrana_ppm=8, tds_producto_final_ppm=5,
                ph=7.0, conductividad_us_cm=15, resistividad_mohm_cm=1.2,
                litros_consumidos_red=500, litros_agua_pura=420)


async def _preparar(crear_cliente, db):
    from datetime import date
    from app.models.contrato import Contrato
    from app.models.equipo import Equipo
    await crear_cliente("20612493821")
    c = Contrato(cliente_ruc="20612493821", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31), monto_mensual_soles=100)
    db.add(c)
    await db.flush()
    db.add(Equipo(serie="RO-1", cliente_ruc="20612493821", contrato_id=c.id, tipo_sistema="OSMOSIS_INVERSA",
                  fecha_instalacion=date(2026, 1, 2), parametros_nominales={"x": 1}))
    await db.flush()
    return c.id


def _body(tecnico_id, contrato_id, **over):
    base = {"id": str(uuid.uuid4()), "contrato_id": contrato_id, "equipo_serie": "RO-1", "tecnico_id": tecnico_id,
            "tipo_intervencion": "PREVENTIVO", "fecha_creacion_cliente": "2026-10-21T15:00:00-05:00",
            "lecturas_agua": LECTURAS, "firma_base64": firma_png(), "gps_latitud": "-8.1116000",
            "gps_longitud": "-79.0288000", "repuestos_consumidos": []}
    base.update(over)
    return base


async def test_post_ordenes_crea_y_devuelve_201(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid), headers=auth_headers(tec))
    assert r.status_code == 201 and r.json()["estado"] == "SINCRONIZADA"


async def test_post_ordenes_mismo_id_dos_veces_200_sin_duplicar(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    body = _body(tec.id, cid)
    r1 = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    r2 = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    assert r1.status_code == 201 and r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.parametrize("campo", list(LECTURAS.keys()))
async def test_post_ordenes_lectura_faltante_422(client, crear_usuario, auth_headers, crear_cliente, db, campo):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    lecturas = {k: v for k, v in LECTURAS.items() if k != campo}
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid, lecturas_agua=lecturas), headers=auth_headers(tec))
    assert r.status_code == 422


async def test_post_ordenes_firma_vacia_422(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid, firma_base64=""), headers=auth_headers(tec))
    assert r.status_code == 422


async def test_post_ordenes_gps_invalido_422(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid, gps_latitud="no-es-numero"), headers=auth_headers(tec))
    assert r.status_code == 422


async def test_post_ordenes_gps_fuera_de_rango_422(client, crear_usuario, auth_headers, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid, gps_latitud="500"), headers=auth_headers(tec))
    assert r.status_code == 422
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid, gps_longitud="-500"), headers=auth_headers(tec))
    assert r.status_code == 422


async def test_post_ordenes_stock_insuficiente_409(client, crear_usuario, auth_headers, crear_cliente, db):
    from app.models.repuesto import Repuesto
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    db.add(Repuesto(codigo="FILT-05", descripcion="x", costo_unitario_soles=1, stock_almacen_central=0))
    await db.flush()
    body = _body(tec.id, cid, repuestos_consumidos=[{"repuesto_codigo": "FILT-05", "cantidad": 1}])
    r = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    assert r.status_code == 409


async def test_post_ordenes_sin_token_401(client, crear_usuario, crear_cliente, db):
    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    r = await client.post("/api/v1/ordenes", json=_body(tec.id, cid))
    assert r.status_code == 401


async def test_post_ordenes_tecnico_de_otro_403(client, crear_usuario, auth_headers, crear_cliente, db):
    tec1 = await crear_usuario("TECNICO")
    tec2 = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    r = await client.post("/api/v1/ordenes", json=_body(tec2.id, cid), headers=auth_headers(tec1))
    assert r.status_code == 403


async def test_contrato_sin_vinculo_409_permita_corregir_y_reintentar_mismo_uuid(
    client, crear_usuario, auth_headers, crear_cliente, gerente_h, db,
):
    from sqlalchemy import func, select
    from app.models.equipo import Equipo
    from app.models.orden import ActaInmutable, OrdenServicio
    from app.models.repuesto import MovimientoInventario, Repuesto

    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    equipo = await db.get(Equipo, "RO-1")
    equipo.contrato_id = None
    repuesto = Repuesto(codigo="FILT-RETRY", descripcion="Filtro", costo_unitario_soles=1, stock_almacen_central=10)
    db.add(repuesto)
    await db.flush()
    body = _body(tec.id, cid, repuestos_consumidos=[{"repuesto_codigo": "FILT-RETRY", "cantidad": 2}])
    response = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    assert response.status_code == 409
    assert "contrato" in response.json()["detail"].lower()
    assert repuesto.stock_almacen_central == 10
    assert (await client.put("/api/v1/equipos/RO-1", json={"contrato_id": cid}, headers=gerente_h)).status_code == 200
    accepted = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    repeated = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    assert accepted.status_code == 201 and repeated.status_code == 200
    assert accepted.json()["id"] == repeated.json()["id"] == body["id"]
    assert repuesto.stock_almacen_central == 8
    for model in (OrdenServicio, ActaInmutable, MovimientoInventario):
        assert await db.scalar(select(func.count()).select_from(model)) == 1


@pytest.mark.parametrize("segundos", [-1, 0, 1], ids=["servicio_previo", "instante_anulacion", "servicio_posterior"])
async def test_anulacion_api_bloquea_servicios_nuevos_y_permite_sincronizar_previos(
    client, crear_usuario, auth_headers, crear_cliente, gerente_h, db, segundos,
):
    from datetime import date, timedelta
    from sqlalchemy import func, select
    from app.models.contrato import CondicionContrato, Contrato
    from app.models.orden import ActaInmutable, OrdenServicio

    tec = await crear_usuario("TECNICO")
    cid = await _preparar(crear_cliente, db)
    contrato = await db.get(Contrato, cid)
    contrato.fecha_inicio = date(2000, 1, 1)
    contrato.fecha_fin = date(2100, 12, 31)
    await db.flush()
    cancelled = await client.post(f"/api/v1/contratos/{cid}/anular", headers=gerente_h)
    assert cancelled.status_code == 200
    await db.refresh(contrato)
    assert contrato.anulado_en is not None
    assert await db.scalar(select(func.count()).select_from(CondicionContrato).where(CondicionContrato.contrato_id == cid)) == 2
    body = _body(tec.id, cid, fecha_creacion_cliente=(contrato.anulado_en + timedelta(seconds=segundos)).isoformat())
    response = await client.post("/api/v1/ordenes", json=body, headers=auth_headers(tec))
    assert response.status_code == (201 if segundos < 0 else 409)
    for model in (OrdenServicio, ActaInmutable):
        assert await db.scalar(select(func.count()).select_from(model)) == (1 if segundos < 0 else 0)
