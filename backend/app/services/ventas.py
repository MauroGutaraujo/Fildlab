from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.venta import Venta, VentaItem
from app.schemas.venta import VentaIn
from app.services.inventario import registrar_movimiento


class ClienteNoEncontrado(Exception):
    pass


class ClienteAnulado(Exception):
    pass


async def crear_venta(session: AsyncSession, datos: VentaIn, usuario_id: int) -> Venta:
    """Venta + items + salidas de stock en una sola unidad atómica.

    Todo ocurre dentro de un SAVEPOINT: si algún item falla (repuesto inexistente,
    stock insuficiente), no queda venta, ni items, ni movimientos, ni descuentos.
    """
    cliente = await session.get(Cliente, datos.cliente_ruc)
    if cliente is None:
        raise ClienteNoEncontrado(datos.cliente_ruc)
    if not cliente.activo:
        raise ClienteAnulado(datos.cliente_ruc)

    total = sum((i.precio_unitario_soles * i.cantidad for i in datos.items), Decimal("0"))
    async with session.begin_nested():
        venta = Venta(cliente_ruc=datos.cliente_ruc, usuario_id=usuario_id, total_soles=total)
        session.add(venta)
        await session.flush()
        # Orden estable por código: evita deadlocks entre ventas concurrentes.
        for item in sorted(datos.items, key=lambda i: i.repuesto_codigo):
            # Primero el movimiento: valida que el repuesto exista y que haya stock.
            await registrar_movimiento(
                session, item.repuesto_codigo, "SALIDA_VENTA", item.cantidad, usuario_id, venta_id=venta.id
            )
            session.add(
                VentaItem(
                    venta_id=venta.id,
                    repuesto_codigo=item.repuesto_codigo,
                    cantidad=item.cantidad,
                    precio_unitario_soles=item.precio_unitario_soles,
                )
            )
    await session.refresh(venta, attribute_names=["items", "total_soles", "fecha"])
    return venta
