import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.orden import ActaInmutable, OrdenServicio
from app.models.repuesto import MovimientoInventario
from app.schemas.orden import OrdenSincronizarIn
from app.services.ordenes import (
    ContratoNoEncontrado, EquipoNoEncontrado, TecnicoNoAutorizado,
    payload_raw_canonico, sincronizar_orden,
)

LECTURAS = dict(tds_entrada_ppm=350, tds_post_membrana_ppm=8, tds_producto_final_ppm=5,
                ph=7.0, conductividad_us_cm=15, resistividad_mohm_cm=1.2,
                litros_consumidos_red=500, litros_agua_pura=420)


@pytest.fixture
async def escenario(crear_cliente, db):
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
    return c


def _datos(tecnico_id, contrato_id, **over):
    base = dict(id=uuid.uuid4(), contrato_id=contrato_id, equipo_serie="RO-1", tecnico_id=tecnico_id,
                tipo_intervencion="PREVENTIVO", fecha_creacion_cliente=datetime.now(timezone.utc),
                lecturas_agua=LECTURAS, firma_base64="AAAA", gps_latitud="-8.1116000",
                gps_longitud="-79.0288000", repuestos_consumidos=[])
    base.update(over)
    return OrdenSincronizarIn(**base)


def test_payload_canonico_es_deterministico_sin_importar_orden_de_claves():
    a = payload_raw_canonico(_datos(1, 1))
    b = payload_raw_canonico(_datos(1, 1))
    assert a == b


async def test_sincronizar_orden_nueva_crea_orden_y_acta(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    orden = await sincronizar_orden(db, _datos(tec.id, escenario.id), tec)
    assert orden.estado == "SINCRONIZADA"
    acta = (await db.execute(select(ActaInmutable).where(ActaInmutable.orden_id == orden.id))).scalar_one()
    assert acta.previous_hash is None


async def test_sincronizar_dos_veces_mismo_id_es_idempotente(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    datos = _datos(tec.id, escenario.id)
    o1 = await sincronizar_orden(db, datos, tec)
    o2 = await sincronizar_orden(db, datos, tec)
    assert o1.id == o2.id
    total = (await db.execute(select(func.count()).select_from(OrdenServicio))).scalar()
    assert total == 1


async def test_segunda_orden_del_mismo_equipo_encadena_hash(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    o1 = await sincronizar_orden(db, _datos(tec.id, escenario.id), tec)
    o2 = await sincronizar_orden(db, _datos(tec.id, escenario.id), tec)
    a1 = (await db.execute(select(ActaInmutable).where(ActaInmutable.orden_id == o1.id))).scalar_one()
    a2 = (await db.execute(select(ActaInmutable).where(ActaInmutable.orden_id == o2.id))).scalar_one()
    assert a2.previous_hash == a1.hash_sha256


async def test_orden_de_otro_equipo_no_hereda_previous_hash(db, escenario, crear_usuario, crear_cliente):
    from datetime import date
    from app.models.equipo import Equipo
    tec = await crear_usuario("TECNICO")
    await sincronizar_orden(db, _datos(tec.id, escenario.id), tec)  # acta en RO-1
    db.add(Equipo(serie="RO-2", cliente_ruc="20612493821", contrato_id=escenario.id, tipo_sistema="OSMOSIS_INVERSA",
                  fecha_instalacion=date(2026, 1, 2), parametros_nominales={"x": 1}))
    await db.flush()
    o2 = await sincronizar_orden(db, _datos(tec.id, escenario.id, equipo_serie="RO-2"), tec)
    a2 = (await db.execute(select(ActaInmutable).where(ActaInmutable.orden_id == o2.id))).scalar_one()
    assert a2.previous_hash is None


async def test_stock_insuficiente_revierte_orden_acta_y_movimientos(db, escenario, crear_usuario):
    from app.models.repuesto import Repuesto
    tec = await crear_usuario("TECNICO")
    db.add(Repuesto(codigo="FILT-05", descripcion="x", costo_unitario_soles=1, stock_almacen_central=0))
    await db.flush()
    with pytest.raises(Exception):
        await sincronizar_orden(
            db, _datos(tec.id, escenario.id, repuestos_consumidos=[{"repuesto_codigo": "FILT-05", "cantidad": 1}]), tec
        )
    assert (await db.execute(select(func.count()).select_from(OrdenServicio))).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(MovimientoInventario))).scalar() == 0


async def test_equipo_inexistente_lanza_EquipoNoEncontrado(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    with pytest.raises(EquipoNoEncontrado):
        await sincronizar_orden(db, _datos(tec.id, escenario.id, equipo_serie="NOPE"), tec)


async def test_contrato_inexistente_lanza_ContratoNoEncontrado(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    with pytest.raises(ContratoNoEncontrado):
        await sincronizar_orden(db, _datos(tec.id, 999999), tec)


async def test_tecnico_no_puede_sincronizar_a_nombre_de_otro(db, escenario, crear_usuario):
    tec1 = await crear_usuario("TECNICO")
    tec2 = await crear_usuario("TECNICO")
    with pytest.raises(TecnicoNoAutorizado):
        await sincronizar_orden(db, _datos(tec2.id, escenario.id), tec1)


async def test_gerencia_puede_sincronizar_a_nombre_de_cualquier_tecnico(db, escenario, crear_usuario):
    tec = await crear_usuario("TECNICO")
    ger = await crear_usuario("GERENCIA")
    orden = await sincronizar_orden(db, _datos(tec.id, escenario.id), ger)
    assert orden.tecnico_id == tec.id
