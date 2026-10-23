import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from orden_helpers import firma_png

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
                tipo_intervencion="PREVENTIVO", fecha_creacion_cliente=datetime(2026, 10, 21, 15, tzinfo=timezone.utc),
                lecturas_agua=LECTURAS, firma_base64=firma_png(), gps_latitud="-8.1116000",
                gps_longitud="-79.0288000", repuestos_consumidos=[])
    base.update(over)
    return OrdenSincronizarIn(**base)


def test_payload_canonico_es_deterministico_para_el_mismo_contenido():
    id_fijo, fecha_fija = uuid.uuid4(), datetime.now(timezone.utc)
    a = payload_raw_canonico(_datos(1, 1, id=id_fijo, fecha_creacion_cliente=fecha_fija))
    b = payload_raw_canonico(_datos(1, 1, id=id_fijo, fecha_creacion_cliente=fecha_fija))
    assert a == b


def test_payload_canonico_cambia_si_cambia_la_firma():
    """RN-04: la firma es parte de lo que se hashea; si no, se podria sustituir sin invalidar el hash."""
    id_fijo, fecha_fija = uuid.uuid4(), datetime.now(timezone.utc)
    a = payload_raw_canonico(_datos(1, 1, id=id_fijo, fecha_creacion_cliente=fecha_fija, firma_base64=firma_png()))
    b = payload_raw_canonico(_datos(1, 1, id=id_fijo, fecha_creacion_cliente=fecha_fija, firma_base64=firma_png(color="blue")))
    assert a != b


def test_payload_canonico_cambia_si_cambia_el_gps():
    id_fijo, fecha_fija = uuid.uuid4(), datetime.now(timezone.utc)
    a = payload_raw_canonico(_datos(1, 1, id=id_fijo, fecha_creacion_cliente=fecha_fija, gps_latitud="-8.0000000"))
    b = payload_raw_canonico(_datos(1, 1, id=id_fijo, fecha_creacion_cliente=fecha_fija, gps_latitud="-9.0000000"))
    assert a != b


def test_payload_canonico_cambia_si_cambia_el_tecnico():
    id_fijo, fecha_fija = uuid.uuid4(), datetime.now(timezone.utc)
    a = payload_raw_canonico(_datos(1, 1, id=id_fijo, fecha_creacion_cliente=fecha_fija))
    b = payload_raw_canonico(_datos(2, 1, id=id_fijo, fecha_creacion_cliente=fecha_fija))
    assert a != b


def test_payload_canonico_cambia_si_cambia_el_id_de_la_orden():
    """Sin esto, dos ordenes distintas del mismo equipo con las mismas lecturas producen
    el mismo hash_sha256 y el hash deja de identificar el acta."""
    fecha_fija = datetime.now(timezone.utc)
    a = payload_raw_canonico(_datos(1, 1, fecha_creacion_cliente=fecha_fija))
    b = payload_raw_canonico(_datos(1, 1, fecha_creacion_cliente=fecha_fija))
    assert a != b  # solo el id (generado distinto por _datos) cambia aqui


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
    assert (await db.execute(select(func.count()).select_from(OrdenServicio))).scalar() == 1
    assert (await db.execute(select(func.count()).select_from(ActaInmutable))).scalar() == 1
    assert (await db.execute(select(func.count()).select_from(MovimientoInventario))).scalar() == 0


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


async def test_dos_sincronizaciones_concurrentes_del_mismo_equipo_no_bifurcan_el_encadenado(engine):
    """Review Focus 2 bajo concurrencia real: dos sesiones distintas sincronizando el mismo
    equipo casi al mismo tiempo no deben leer el mismo previous_hash (eso bifurcaria la cadena)."""
    import asyncio
    from datetime import date

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.security import hash_password
    from app.models.cliente import Cliente
    from app.models.contrato import Contrato
    from app.models.equipo import Equipo
    from app.models.usuario import Usuario

    ruc = "20977777701"
    async with AsyncSession(engine, expire_on_commit=False) as s:
        s.add(Cliente(ruc=ruc, razon_social="x", direccion="y"))
        c = Contrato(cliente_ruc=ruc, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31), monto_mensual_soles=100)
        s.add(c)
        await s.flush()
        s.add(Equipo(serie="RO-CONC", cliente_ruc=ruc, contrato_id=c.id, tipo_sistema="OSMOSIS_INVERSA",
                     fecha_instalacion=date(2026, 1, 2), parametros_nominales={"x": 1}))
        tec = Usuario(nombre="Conc", email="conc-orden@test.pe", password_hash=hash_password("x"), rol="TECNICO")
        s.add(tec)
        await s.commit()
        contrato_id, tecnico_id = c.id, tec.id

    async def sincronizar():
        async with AsyncSession(engine, expire_on_commit=False) as s:
            tec_local = await s.get(Usuario, tecnico_id)
            orden = await sincronizar_orden(s, _datos(tecnico_id, contrato_id, equipo_serie="RO-CONC"), tec_local)
            await s.commit()
            return orden.id

    try:
        id1, id2 = await asyncio.gather(sincronizar(), sincronizar())
        async with AsyncSession(engine) as s:
            a1 = (await s.execute(select(ActaInmutable).where(ActaInmutable.orden_id == id1))).scalar_one()
            a2 = (await s.execute(select(ActaInmutable).where(ActaInmutable.orden_id == id2))).scalar_one()
            # Exactamente una es la "primera" (previous_hash NULL) y la otra encadena con ella.
            # Si el lock fallara, ambas leerian NULL (cadena bifurcada) o ninguna encadenaria bien.
            primeras = [a for a in (a1, a2) if a.previous_hash is None]
            segundas = [a for a in (a1, a2) if a.previous_hash is not None]
            assert len(primeras) == 1 and len(segundas) == 1
            assert segundas[0].previous_hash == primeras[0].hash_sha256
    finally:
        async with AsyncSession(engine) as s:
            from sqlalchemy import delete

            await s.execute(delete(ActaInmutable).where(ActaInmutable.orden_id.in_([id1, id2])))
            await s.execute(delete(OrdenServicio).where(OrdenServicio.id.in_([id1, id2])))
            await s.execute(delete(Equipo).where(Equipo.serie == "RO-CONC"))
            await s.execute(delete(Contrato).where(Contrato.id == contrato_id))
            await s.execute(delete(Usuario).where(Usuario.id == tecnico_id))
            await s.execute(delete(Cliente).where(Cliente.ruc == ruc))
            await s.commit()
