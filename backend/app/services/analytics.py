from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.contrato import Contrato
from app.models.orden import OrdenServicio
from app.models.repuesto import MovimientoInventario, Repuesto


def _rango_mes(periodo: str) -> tuple[datetime, datetime]:
    """periodo ya viene validado como YYYY-MM por el schema Periodo. Devuelve [inicio, fin) en UTC."""
    anio, mes = (int(x) for x in periodo.split("-"))
    inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
    fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc) if mes == 12 else datetime(anio, mes + 1, 1, tzinfo=timezone.utc)
    return inicio, fin


async def rentabilidad_por_contrato(session: AsyncSession, periodo: str) -> list[dict]:
    inicio, fin = _rango_mes(periodo)

    contratos = (
        await session.execute(
            select(Contrato, Cliente.razon_social)
            .join(Cliente, Cliente.ruc == Contrato.cliente_ruc)
            .where(Contrato.fecha_inicio < fin.date(), Contrato.fecha_fin >= inicio.date())
            .order_by(Contrato.id)
        )
    ).all()

    costos_q = (
        select(
            OrdenServicio.contrato_id,
            func.sum(MovimientoInventario.cantidad * Repuesto.costo_unitario_soles).label("costo"),
        )
        .select_from(MovimientoInventario)
        .join(OrdenServicio, OrdenServicio.id == MovimientoInventario.orden_id)
        .join(Repuesto, Repuesto.codigo == MovimientoInventario.repuesto_codigo)
        .where(
            MovimientoInventario.tipo == "SALIDA_ORDEN",
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
