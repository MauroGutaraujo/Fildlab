import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repuesto import TIPOS_MOVIMIENTO, MovimientoInventario, Repuesto

_SUMAN = {"ENTRADA", "AJUSTE_ENTRADA"}


class InventarioError(Exception):
    """Base de errores de dominio del inventario."""


class RepuestoNoEncontrado(InventarioError):
    pass


class StockInsuficiente(InventarioError):
    pass


class MovimientoInvalido(InventarioError):
    pass


async def registrar_movimiento(
    session: AsyncSession,
    codigo: str,
    tipo: str,
    cantidad: int,
    usuario_id: int,
    orden_id: uuid.UUID | None = None,
    venta_id: int | None = None,
) -> MovimientoInventario:
    """Aplica el movimiento al stock central de forma atómica.

    Bloquea la fila del repuesto (SELECT ... FOR UPDATE): dos salidas concurrentes
    se serializan y la segunda ve el stock ya descontado.
    """
    if tipo not in TIPOS_MOVIMIENTO:
        raise MovimientoInvalido(f"Tipo de movimiento desconocido: {tipo}")
    if cantidad <= 0:
        raise MovimientoInvalido("La cantidad debe ser mayor que cero")
    if tipo == "SALIDA_ORDEN" and orden_id is None:
        raise MovimientoInvalido("SALIDA_ORDEN requiere orden_id")
    if tipo == "SALIDA_VENTA" and venta_id is None:
        raise MovimientoInvalido("SALIDA_VENTA requiere venta_id")

    repuesto = (
        await session.execute(select(Repuesto).where(Repuesto.codigo == codigo).with_for_update().execution_options(populate_existing=True))
    ).scalar_one_or_none()
    if repuesto is None:
        raise RepuestoNoEncontrado(codigo)

    delta = cantidad if tipo in _SUMAN else -cantidad
    if repuesto.stock_almacen_central + delta < 0:
        raise StockInsuficiente(f"{codigo}: stock {repuesto.stock_almacen_central}, se piden {cantidad}")
    repuesto.stock_almacen_central += delta

    mov = MovimientoInventario(
        repuesto_codigo=codigo, tipo=tipo, cantidad=cantidad, orden_id=orden_id, venta_id=venta_id, usuario_id=usuario_id,
        costo_unitario_soles=repuesto.costo_unitario_soles, costo_historico_confirmado=True,
    )
    session.add(mov)
    await session.flush()
    await session.refresh(mov)
    return mov
