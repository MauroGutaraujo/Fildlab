from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.models.orden import OrdenServicio
from app.models.repuesto import MovimientoInventario, Repuesto

LIMA = ZoneInfo("America/Lima")


def _rango_mes(periodo: str) -> tuple[datetime, datetime]:
    """periodo ya viene validado como YYYY-MM por el schema Periodo. "Mes calendario" es el mes del negocio
    (Trujillo, Peru, UTC-5) — no UTC. Convertimos el limite de mes en hora de Lima al instante UTC
    equivalente, para comparar contra fecha_creacion_cliente (timestamptz) por instante absoluto."""
    anio, mes = (int(x) for x in periodo.split("-"))
    inicio_lima = datetime(anio, mes, 1, tzinfo=LIMA)
    fin_lima = datetime(anio + 1, 1, 1, tzinfo=LIMA) if mes == 12 else datetime(anio, mes + 1, 1, tzinfo=LIMA)
    return inicio_lima, fin_lima


async def rentabilidad_por_contrato(session: AsyncSession, periodo: str) -> list[dict]:
    inicio, fin = _rango_mes(periodo)

    contratos = (
        await session.execute(
            select(Contrato, Cliente.razon_social)
            .join(Cliente, Cliente.ruc == Contrato.cliente_ruc)
            .where(
                Contrato.fecha_inicio < fin.date(),
                Contrato.fecha_fin >= inicio.date(),
                Contrato.estado != "ANULADO",
            )
            .order_by(Contrato.id)
        )
    ).all()

    # RN-04: una adenda nunca edita el acta firmada; registra el ajuste como AJUSTE_SALIDA (consumo
    # adicional hallado despues) o AJUSTE_ENTRADA (stock devuelto). El costo "real" del periodo debe
    # reflejar esas correcciones, no solo el consumo original de SALIDA_ORDEN.
    signo = case((MovimientoInventario.tipo == "AJUSTE_ENTRADA", -1), else_=1)
    costos_q = (
        select(
            OrdenServicio.contrato_id,
            func.sum(MovimientoInventario.cantidad * Repuesto.costo_unitario_soles * signo).label("costo"),
        )
        .select_from(MovimientoInventario)
        .join(OrdenServicio, OrdenServicio.id == MovimientoInventario.orden_id)
        .join(Repuesto, Repuesto.codigo == MovimientoInventario.repuesto_codigo)
        .where(
            MovimientoInventario.tipo.in_(("SALIDA_ORDEN", "AJUSTE_SALIDA", "AJUSTE_ENTRADA")),
            OrdenServicio.estado == "LIQUIDADA",
            OrdenServicio.fecha_creacion_cliente >= inicio,
            OrdenServicio.fecha_creacion_cliente < fin,
        )
        .group_by(OrdenServicio.contrato_id)
    )
    costos = {contrato_id: costo for contrato_id, costo in (await session.execute(costos_q)).all()}

    resultado = []
    for contrato, razon_social in contratos:
        ingreso = contrato.monto_mensual_soles
        costo = costos.get(contrato.id) or Decimal("0.00")
        margen = ingreso - costo
        margen_pct = float(margen / ingreso * 100) if ingreso > 0 else None
        resultado.append(
            {
                "contrato_id": contrato.id,
                "cliente_ruc": contrato.cliente_ruc,
                "razon_social": razon_social,
                "ingreso_soles": ingreso,
                "costo_repuestos_soles": costo,
                "margen_soles": margen,
                "margen_pct": margen_pct,
            }
        )
    return resultado


async def cumplimiento_sla(session: AsyncSession, periodo: str) -> dict:
    inicio, fin = _rango_mes(periodo)

    total_ordenes = (
        await session.execute(
            select(func.count())
            .select_from(OrdenServicio)
            .where(OrdenServicio.fecha_creacion_cliente >= inicio, OrdenServicio.fecha_creacion_cliente < fin)
        )
    ).scalar_one()

    # RN-02/REQ-15 todavia no tiene ningun productor de tiempo_respuesta_horas en el sistema (columna
    # declarada pero nunca escrita). Si lo tratamos como "cumple", el tablero muestra 100% falso. Se
    # distinguen las ordenes medidas de las que no, y el % de cumplimiento se calcula solo sobre las medidas.
    medidas = (
        await session.execute(
            select(func.count())
            .select_from(OrdenServicio)
            .where(
                OrdenServicio.fecha_creacion_cliente >= inicio,
                OrdenServicio.fecha_creacion_cliente < fin,
                OrdenServicio.tiempo_respuesta_horas.is_not(None),
            )
        )
    ).scalar_one()

    filas = (
        await session.execute(
            select(
                OrdenServicio.id,
                OrdenServicio.equipo_serie,
                OrdenServicio.tiempo_respuesta_horas,
                Contrato.sla_horas_max_respuesta,
                Cliente.razon_social,
            )
            .select_from(OrdenServicio)
            .join(Contrato, Contrato.id == OrdenServicio.contrato_id)
            .join(Cliente, Cliente.ruc == Contrato.cliente_ruc)
            .where(
                OrdenServicio.fecha_creacion_cliente >= inicio,
                OrdenServicio.fecha_creacion_cliente < fin,
                OrdenServicio.tiempo_respuesta_horas > Contrato.sla_horas_max_respuesta,
            )
            .order_by(OrdenServicio.fecha_creacion_cliente)
        )
    ).all()

    ordenes_fuera_sla = [
        {
            "orden_id": orden_id,
            "equipo_serie": equipo_serie,
            "razon_social": razon_social,
            "tiempo_respuesta_horas": tiempo,
            "sla_horas_max_respuesta": sla_max,
        }
        for orden_id, equipo_serie, tiempo, sla_max, razon_social in filas
    ]

    pct_cumplimiento = (medidas - len(ordenes_fuera_sla)) / medidas * 100 if medidas > 0 else None

    return {
        "total_ordenes": total_ordenes,
        "ordenes_sin_medicion": total_ordenes - medidas,
        "ordenes_fuera_sla": ordenes_fuera_sla,
        "pct_cumplimiento": pct_cumplimiento,
    }
