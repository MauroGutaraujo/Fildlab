import { db } from "./dexie";

export async function cargarStockTurno(
  items: { repuesto_codigo: string; cantidad: number }[],
  turnoId: string,
): Promise<void> {
  await db.stockMovilLocal.bulkPut(
    items.map((i) => ({ repuesto_codigo: i.repuesto_codigo, cantidad_cargada: i.cantidad, cantidad_consumida: 0, turno_id: turnoId })),
  );
}

export async function consumir(codigo: string, cantidad: number): Promise<{ ok: true } | { ok: false; motivo: string }> {
  const item = await db.stockMovilLocal.get(codigo);
  if (!item) return { ok: false, motivo: "No hay stock móvil cargado para ese repuesto" };
  if (item.cantidad_consumida + cantidad > item.cantidad_cargada) {
    return { ok: false, motivo: "Stock móvil insuficiente" };
  }
  await db.stockMovilLocal.update(codigo, { cantidad_consumida: item.cantidad_consumida + cantidad });
  return { ok: true };
}
