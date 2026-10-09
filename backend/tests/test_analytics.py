import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio
from app.models.repuesto import MovimientoInventario, Repuesto


async def _contrato(db, crear_cliente, *, ruc="20612493821", monto="2500.00", sla=4,
                     inicio=date(2026, 1, 1), fin=date(2026, 12, 31)):
    await crear_cliente(ruc)
    c = Contrato(cliente_ruc=ruc, fecha_inicio=inicio, fecha_fin=fin,
                 monto_mensual_soles=Decimal(monto), sla_horas_max_respuesta=sla)
    db.add(c)
    await db.flush()
    return c


async def _orden(db, contrato, crear_usuario, *, estado="LIQUIDADA", fecha, tiempo_respuesta=None):
    tecnico = await crear_usuario("TECNICO")
    serie = f"SER-{uuid.uuid4().hex[:8]}"
    db.add(Equipo(serie=serie, cliente_ruc=contrato.cliente_ruc, contrato_id=contrato.id,
                  tipo_sistema="OSMOSIS_INVERSA", fecha_instalacion=date(2026, 1, 2),
                  parametros_nominales={"presion_psi": 60}))
    await db.flush()
    o = OrdenServicio(id=uuid.uuid4(), contrato_id=contrato.id, equipo_serie=serie, tecnico_id=tecnico.id,
                      tipo_intervencion="PREVENTIVO", estado=estado,
                      fecha_creacion_cliente=fecha, tiempo_respuesta_horas=tiempo_respuesta)
    db.add(o)
    await db.flush()
    return o


async def _consumo(db, orden, usuario_id, *, repuesto_codigo="FILT-05", cantidad=2, costo_unitario="5.00", tipo="SALIDA_ORDEN"):
    rep = await db.get(Repuesto, repuesto_codigo)
    if rep is None:
        rep = Repuesto(codigo=repuesto_codigo, descripcion=repuesto_codigo, costo_unitario_soles=Decimal(costo_unitario))
        db.add(rep)
        await db.flush()
    db.add(MovimientoInventario(repuesto_codigo=repuesto_codigo, tipo=tipo, cantidad=cantidad,
                                orden_id=orden.id, usuario_id=usuario_id))
    await db.flush()


async def test_rentabilidad_solo_gerencia(client, tecnico_h):
    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=tecnico_h)
    assert r.status_code == 403


async def test_rentabilidad_sin_token_401(client):
    assert (await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09")).status_code == 401


async def test_rentabilidad_periodo_invalido_422(client, gerente_h):
    for periodo in ("2026-13", "abc", "", "2026-9"):
        r = await client.get(f"/api/v1/analytics/rentabilidad?periodo={periodo}", headers=gerente_h)
        assert r.status_code == 422, periodo
    assert (await client.get("/api/v1/analytics/rentabilidad", headers=gerente_h)).status_code == 422


async def test_rentabilidad_sin_contratos_en_el_mes_lista_vacia(client, gerente_h):
    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.status_code == 200
    assert r.json() == {"periodo": "2026-09", "contratos": []}


async def test_rentabilidad_calcula_ingreso_costo_y_margen(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, monto="2500.00")
    orden = await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                         fecha=datetime(2026, 9, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id, cantidad=2, costo_unitario="5.00")  # 2 x 5.00 = 10.00
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.status_code == 200
    c = r.json()["contratos"][0]
    assert c["contrato_id"] == contrato.id
    assert c["ingreso_soles"] == "2500.00"
    assert c["costo_repuestos_soles"] == "10.00"
    assert c["margen_soles"] == "2490.00"
    assert c["margen_pct"] == pytest.approx(99.6)


async def test_rentabilidad_orden_comprometida_no_liquidada_no_suma_costo(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, estado="COMPROMETIDA",
                         fecha=datetime(2026, 9, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id)
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    c = r.json()["contratos"][0]
    assert c["costo_repuestos_soles"] == "0.00" or c["costo_repuestos_soles"] == "0"


async def test_rentabilidad_orden_de_otro_mes_no_se_cuenta(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                         fecha=datetime(2026, 8, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id)
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    c = r.json()["contratos"][0]
    assert c["costo_repuestos_soles"] in ("0.00", "0")


async def test_rentabilidad_contrato_fuera_de_rango_del_mes_no_aparece(client, gerente_h, db, crear_cliente):
    await _contrato(db, crear_cliente, inicio=date(2025, 1, 1), fin=date(2026, 6, 30))  # termina antes de sept.
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.json()["contratos"] == []


async def test_rentabilidad_contrato_anulado_no_aparece(client, gerente_h, db, crear_cliente):
    contrato = await _contrato(db, crear_cliente)
    contrato.estado = "ANULADO"
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.json()["contratos"] == []


async def test_rentabilidad_corta_el_mes_en_hora_de_lima_no_utc(client, gerente_h, db, crear_cliente, crear_usuario):
    """2026-10-01 04:30 UTC es 2026-09-30 23:30 en Lima (UTC-5): debe seguir contando como septiembre."""
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                         fecha=datetime(2026, 10, 1, 4, 30, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id, cantidad=1, costo_unitario="5.00")
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.json()["contratos"][0]["costo_repuestos_soles"] == "5.00"

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-10", headers=gerente_h)
    assert r.json()["contratos"][0]["costo_repuestos_soles"] in ("0.00", "0")


async def test_sla_corta_el_mes_en_hora_de_lima_no_utc(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente)
    await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 10, 1, 4, 30, tzinfo=timezone.utc))
    await db.commit()

    assert (await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)).json()["total_ordenes"] == 1
    assert (await client.get("/api/v1/analytics/sla?periodo=2026-10", headers=gerente_h)).json()["total_ordenes"] == 0


async def test_rentabilidad_ajuste_salida_de_adenda_suma_costo(client, gerente_h, db, crear_cliente, crear_usuario):
    """RN-04: una adenda que descubre consumo adicional genera AJUSTE_SALIDA — debe sumar al costo real."""
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                         fecha=datetime(2026, 9, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id, cantidad=2, costo_unitario="5.00", tipo="SALIDA_ORDEN")  # 10.00
    await _consumo(db, orden, orden.tecnico_id, cantidad=1, costo_unitario="5.00", tipo="AJUSTE_SALIDA")  # +5.00
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.json()["contratos"][0]["costo_repuestos_soles"] == "15.00"


async def test_rentabilidad_ajuste_entrada_de_adenda_resta_costo(client, gerente_h, db, crear_cliente, crear_usuario):
    """RN-04: una adenda que devuelve stock genera AJUSTE_ENTRADA — debe restar del costo real."""
    contrato = await _contrato(db, crear_cliente)
    orden = await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                         fecha=datetime(2026, 9, 15, tzinfo=timezone.utc))
    await _consumo(db, orden, orden.tecnico_id, cantidad=3, costo_unitario="5.00", tipo="SALIDA_ORDEN")  # 15.00
    await _consumo(db, orden, orden.tecnico_id, cantidad=1, costo_unitario="5.00", tipo="AJUSTE_ENTRADA")  # -5.00
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    assert r.json()["contratos"][0]["costo_repuestos_soles"] == "10.00"


async def test_rentabilidad_dos_contratos_no_mezclan_costos(client, gerente_h, db, crear_cliente, crear_usuario):
    c1 = await _contrato(db, crear_cliente, ruc="20612493821")
    c2 = await _contrato(db, crear_cliente, ruc="20100047218")
    o1 = await _orden(db, c1, crear_usuario, estado="LIQUIDADA", fecha=datetime(2026, 9, 10, tzinfo=timezone.utc))
    o2 = await _orden(db, c2, crear_usuario, estado="LIQUIDADA", fecha=datetime(2026, 9, 11, tzinfo=timezone.utc))
    await _consumo(db, o1, o1.tecnico_id, repuesto_codigo="FILT-05", cantidad=1, costo_unitario="5.00")
    await _consumo(db, o2, o2.tecnico_id, repuesto_codigo="FILT-05", cantidad=3, costo_unitario="5.00")
    await db.commit()

    r = await client.get("/api/v1/analytics/rentabilidad?periodo=2026-09", headers=gerente_h)
    por_id = {c["contrato_id"]: c["costo_repuestos_soles"] for c in r.json()["contratos"]}
    assert por_id[c1.id] == "5.00"
    assert por_id[c2.id] == "15.00"


async def test_sla_solo_gerencia(client, tecnico_h):
    assert (await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=tecnico_h)).status_code == 403


async def test_sla_periodo_invalido_422(client, gerente_h):
    assert (await client.get("/api/v1/analytics/sla?periodo=no-es-un-mes", headers=gerente_h)).status_code == 422


async def test_sla_sin_ordenes_en_el_mes(client, gerente_h):
    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    assert r.status_code == 200
    assert r.json() == {
        "periodo": "2026-09", "total_ordenes": 0, "ordenes_sin_medicion": 0,
        "ordenes_fuera_sla": [], "pct_cumplimiento": None,
    }


async def test_sla_orden_que_excede_el_maximo_aparece_en_fuera_de_sla(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, estado="SINCRONIZADA",
                fecha=datetime(2026, 9, 10, tzinfo=timezone.utc), tiempo_respuesta=Decimal("9.50"))
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    b = r.json()
    assert b["total_ordenes"] == 1
    assert len(b["ordenes_fuera_sla"]) == 1
    assert b["ordenes_fuera_sla"][0]["tiempo_respuesta_horas"] == "9.50"
    assert b["ordenes_fuera_sla"][0]["sla_horas_max_respuesta"] == 4
    assert b["pct_cumplimiento"] == pytest.approx(0.0)


async def test_sla_orden_exactamente_en_el_limite_cuenta_como_cumplida(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 9, 10, tzinfo=timezone.utc),
                tiempo_respuesta=Decimal("4.00"))
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    b = r.json()
    assert b["ordenes_fuera_sla"] == []
    assert b["pct_cumplimiento"] == pytest.approx(100.0)


async def test_sla_orden_sin_tiempo_de_respuesta_aun_no_rompe_el_calculo(client, gerente_h, db, crear_cliente, crear_usuario):
    """Sin ninguna orden medida, pct_cumplimiento es None (no 100%) — no se puede afirmar
    cumplimiento sobre mediciones que no existen todavia."""
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 9, 10, tzinfo=timezone.utc), tiempo_respuesta=None)
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    b = r.json()
    assert b["total_ordenes"] == 1
    assert b["ordenes_sin_medicion"] == 1
    assert b["ordenes_fuera_sla"] == []
    assert b["pct_cumplimiento"] is None


async def test_sla_pct_cumplimiento_se_calcula_solo_sobre_ordenes_medidas(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 9, 10, tzinfo=timezone.utc),
                tiempo_respuesta=Decimal("9.00"))  # fuera de SLA
    await _orden(db, contrato, crear_usuario, fecha=datetime(2026, 9, 11, tzinfo=timezone.utc), tiempo_respuesta=None)
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    b = r.json()
    assert b["total_ordenes"] == 2
    assert b["ordenes_sin_medicion"] == 1
    assert len(b["ordenes_fuera_sla"]) == 1
    assert b["pct_cumplimiento"] == pytest.approx(0.0)  # 1 de 1 orden medida esta fuera de SLA


async def test_sla_cuenta_ordenes_sin_importar_el_estado(client, gerente_h, db, crear_cliente, crear_usuario):
    contrato = await _contrato(db, crear_cliente, sla=4)
    await _orden(db, contrato, crear_usuario, estado="SINCRONIZADA",
                fecha=datetime(2026, 9, 5, tzinfo=timezone.utc), tiempo_respuesta=Decimal("2.00"))
    await _orden(db, contrato, crear_usuario, estado="COMPROMETIDA",
                fecha=datetime(2026, 9, 6, tzinfo=timezone.utc), tiempo_respuesta=Decimal("2.00"))
    await _orden(db, contrato, crear_usuario, estado="LIQUIDADA",
                fecha=datetime(2026, 9, 7, tzinfo=timezone.utc), tiempo_respuesta=Decimal("2.00"))
    await db.commit()

    r = await client.get("/api/v1/analytics/sla?periodo=2026-09", headers=gerente_h)
    assert r.json()["total_ordenes"] == 3
