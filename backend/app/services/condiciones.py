from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contrato import CondicionContrato, Contrato


def proximo_mes() -> date:
    hoy = datetime.now(ZoneInfo("America/Lima")).date()
    return date(hoy.year + 1, 1, 1) if hoy.month == 12 else date(hoy.year, hoy.month + 1, 1)


async def guardar_condicion(session: AsyncSession, contrato: Contrato, desde: date, origen: str) -> None:
    session.add(CondicionContrato(
        contrato_id=contrato.id, vigente_desde=desde, fecha_inicio=contrato.fecha_inicio,
        fecha_fin=contrato.fecha_fin, monto_mensual_soles=contrato.monto_mensual_soles,
        sla_horas_max_respuesta=contrato.sla_horas_max_respuesta, estado=contrato.estado, origen=origen,
    ))
    await session.flush()


async def asegurar_base(session: AsyncSession, contrato: Contrato) -> None:
    existe = await session.scalar(select(CondicionContrato.id).where(CondicionContrato.contrato_id == contrato.id).limit(1))
    if existe is None:
        await guardar_condicion(session, contrato, date.min, "BASE_LEGADA")


async def condiciones_en_fecha(session: AsyncSession, contrato: Contrato, fecha: date) -> CondicionContrato | Contrato:
    condicion = await session.scalar(select(CondicionContrato).where(
        CondicionContrato.contrato_id == contrato.id, CondicionContrato.vigente_desde <= fecha,
    ).order_by(CondicionContrato.vigente_desde.desc(), CondicionContrato.id.desc()).limit(1))
    return condicion if condicion is not None else contrato
