import asyncio
import uuid
from datetime import date

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.models.equipo import Equipo
from app.models.orden import ActaInmutable, AdendaCorreccion, OrdenServicio
from app.models.repuesto import MovimientoInventario, Repuesto
from app.models.usuario import Usuario
from app.schemas.liquidacion import AdendaIn
from app.services import liquidacion, ordenes
from test_ordenes_service import _datos


@pytest.fixture
async def concurrente(engine):
    suffix = uuid.uuid4().hex[:10]
    ruc = str(uuid.uuid4().int)[:11]
    series = [f"CON-{suffix}-1", f"CON-{suffix}-2"]
    codigos = [f"REP-{suffix}-1", f"REP-{suffix}-2"]
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(Cliente(ruc=ruc, razon_social="Concurrencia", direccion="Lima"))
        await session.flush()
        contrato = Contrato(cliente_ruc=ruc, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31), monto_mensual_soles=100)
        tecnico = Usuario(nombre="Concurrencia", email=f"{suffix}@test.pe", password_hash="test", rol="TECNICO")
        session.add_all([contrato, tecnico])
        await session.flush()
        for serie in series:
            session.add(Equipo(serie=serie, cliente_ruc=ruc, contrato_id=contrato.id, tipo_sistema="FILTRO",
                               fecha_instalacion=date(2026, 1, 1), parametros_nominales={}))
        for codigo in codigos:
            session.add(Repuesto(codigo=codigo, descripcion="Prueba", costo_unitario_soles=1, stock_almacen_central=10))
        await session.commit()
        seed = dict(contrato=contrato.id, tecnico=tecnico.id, series=series, codigos=codigos)
    try:
        yield seed
    finally:
        async with AsyncSession(engine) as session:
            ids = select(OrdenServicio.id).where(OrdenServicio.equipo_serie.in_(series))
            await session.execute(delete(MovimientoInventario).where(MovimientoInventario.repuesto_codigo.in_(codigos)))
            await session.execute(delete(AdendaCorreccion).where(AdendaCorreccion.orden_id.in_(ids)))
            await session.execute(delete(ActaInmutable).where(ActaInmutable.orden_id.in_(ids)))
            await session.execute(delete(OrdenServicio).where(OrdenServicio.equipo_serie.in_(series)))
            await session.execute(delete(Equipo).where(Equipo.serie.in_(series)))
            await session.execute(delete(Repuesto).where(Repuesto.codigo.in_(codigos)))
            await session.execute(delete(Contrato).where(Contrato.id == seed["contrato"]))
            await session.execute(delete(Usuario).where(Usuario.id == seed["tecnico"]))
            await session.execute(delete(Cliente).where(Cliente.ruc == ruc))
            await session.commit()


def datos(seed, *, equipo=0, **overrides):
    return _datos(seed["tecnico"], seed["contrato"], equipo_serie=seed["series"][equipo], **overrides)


async def sync(engine, seed, body):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(Usuario, seed["tecnico"])
        order = await ordenes.sincronizar_orden(session, body, user)
        await session.commit()
        return order.id


async def test_reintentos_simultaneos_uuid_no_duplican_acta_ni_consumo(engine, concurrente):
    body = datos(concurrente, repuestos_consumidos=[{"repuesto_codigo": concurrente["codigos"][0], "cantidad": 2}])
    async with AsyncSession(engine) as guard:
        await guard.execute(select(Equipo).where(Equipo.serie == concurrente["series"][0]).with_for_update())
        first = asyncio.create_task(sync(engine, concurrente, body))
        second = asyncio.create_task(sync(engine, concurrente, body))
        try:
            await asyncio.sleep(0.15)
        finally:
            await guard.rollback()
        ids = await asyncio.wait_for(asyncio.gather(first, second, return_exceptions=True), timeout=10)
    assert ids == [body.id, body.id]
    async with AsyncSession(engine) as session:
        assert await session.scalar(select(func.count()).select_from(ActaInmutable).where(ActaInmutable.orden_id == body.id)) == 1
        assert await session.scalar(select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.orden_id == body.id)) == 1
        assert (await session.get(Repuesto, concurrente["codigos"][0])).stock_almacen_central == 8


async def test_inicio_transacciones_invertido_no_regresa_cabeza(engine, concurrente):
    async with AsyncSession(engine, expire_on_commit=False) as started_first:
        await started_first.execute(text("SELECT CURRENT_TIMESTAMP"))
        first_id = await sync(engine, concurrente, datos(concurrente))
        user = await started_first.get(Usuario, concurrente["tecnico"])
        second = await ordenes.sincronizar_orden(started_first, datos(concurrente), user)
        await started_first.commit()
    third_id = await sync(engine, concurrente, datos(concurrente))
    async with AsyncSession(engine) as session:
        acts = list((await session.scalars(select(ActaInmutable).where(ActaInmutable.orden_id.in_([first_id, second.id, third_id])))).all())
        by_order = {a.orden_id: a for a in acts}
        assert by_order[second.id].creado_en < by_order[first_id].creado_en
        assert by_order[third_id].previous_hash == by_order[second.id].hash_sha256
        assert [by_order[i].secuencia for i in [first_id, second.id, third_id]] == [1, 2, 3]


@pytest.mark.parametrize("adendas", [False, True])
async def test_repuestos_en_orden_inverso_no_generan_deadlock(engine, concurrente, monkeypatch, adendas):
    module = liquidacion if adendas else ordenes
    original = module.registrar_movimiento

    async def registrar_con_solapamiento(*args, **kwargs):
        movement = await original(*args, **kwargs)
        await asyncio.sleep(0.05)  # Mantiene locks reales y hace solapar las dos transacciones.
        return movement

    monkeypatch.setattr(module, "registrar_movimiento", registrar_con_solapamiento)
    codes = concurrente["codigos"]
    if adendas:
        order_ids = [await sync(engine, concurrente, datos(concurrente, equipo=i)) for i in range(2)]

        async def update(index, ordered_codes):
            async with AsyncSession(engine) as session:
                await liquidacion.crear_adenda(session, order_ids[index], concurrente["tecnico"],
                    AdendaIn(observacion="Corrección", ajuste_repuestos=[{"repuesto_codigo": c, "delta": -1} for c in ordered_codes]))
                await session.commit()
    else:
        async def update(index, ordered_codes):
            await sync(engine, concurrente, datos(concurrente, equipo=index,
                repuestos_consumidos=[{"repuesto_codigo": c, "cantidad": 1} for c in ordered_codes]))

    results = await asyncio.wait_for(asyncio.gather(update(0, codes), update(1, list(reversed(codes))), return_exceptions=True), timeout=10)
    assert not [r for r in results if isinstance(r, BaseException)]
    async with AsyncSession(engine) as session:
        for code in codes:
            assert (await session.get(Repuesto, code)).stock_almacen_central == 8
