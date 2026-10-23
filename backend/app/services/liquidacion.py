import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orden import AdendaCorreccion, OrdenServicio
from app.schemas.liquidacion import AdendaIn
from app.services.inventario import registrar_movimiento


class OrdenNoEncontrada(Exception):
    pass


class OrdenYaLiquidada(Exception):
    pass


async def _orden_bloqueada(session: AsyncSession, orden_id: uuid.UUID) -> OrdenServicio:
    orden = (
        await session.execute(select(OrdenServicio).where(OrdenServicio.id == orden_id).with_for_update())
    ).scalar_one_or_none()
    if orden is None:
        raise OrdenNoEncontrada(str(orden_id))
    return orden


async def liquidar(session: AsyncSession, orden_id: uuid.UUID) -> OrdenServicio:
    """RN-03 fase 2: la Gerencia consolida la baja contable. Solo cambia el estado;
    el acta firmada (RN-04) no se toca."""
    orden = await _orden_bloqueada(session, orden_id)
    if orden.estado == "LIQUIDADA":
        raise OrdenYaLiquidada(str(orden_id))
    orden.estado = "LIQUIDADA"
    await session.flush()
    return orden


async def crear_adenda(session: AsyncSession, orden_id: uuid.UUID, gerente_id: int, datos: AdendaIn) -> AdendaCorreccion:
    """RN-04: las correcciones se registran como adenda vinculada; el acta nunca se edita.

    Adenda + ajustes de stock forman una unidad atómica (SAVEPOINT)."""
    await _orden_bloqueada(session, orden_id)
    ajustes = datos.ajuste_repuestos or []
    async with session.begin_nested():
        for a in sorted(ajustes, key=lambda item: item.repuesto_codigo):
            tipo = "AJUSTE_ENTRADA" if a.delta > 0 else "AJUSTE_SALIDA"
            await registrar_movimiento(session, a.repuesto_codigo, tipo, abs(a.delta), gerente_id, orden_id=orden_id)
        adenda = AdendaCorreccion(
            orden_id=orden_id,
            gerente_id=gerente_id,
            observacion=datos.observacion,
            ajuste_repuestos=[a.model_dump() for a in ajustes] or None,
        )
        session.add(adenda)
        await session.flush()
    await session.refresh(adenda)
    return adenda
