import { db } from "./dexie";

export async function cargarStockTurno(
  items: { repuesto_codigo: string; cantidad: number }[],
  turnoId: string,
): Promise<void> {
  // Sumar a lo ya cargado y conservar el consumo: recargar a mitad de turno (el caso normal,
  // "me quedaba 1, cargué 5 más") no debe borrar lo que el técnico ya consumió.
  await db.transaction("rw", db.stockMovilLocal, async () => {
    for (const i of items) {
      const previo = await db.stockMovilLocal.get(i.repuesto_codigo);
      await db.stockMovilLocal.put({
        repuesto_codigo: i.repuesto_codigo,
        cantidad_cargada: (previo?.cantidad_cargada ?? 0) + i.cantidad,
        cantidad_consumida: previo?.cantidad_consumida ?? 0,
        turno_id: turnoId,
      });
    }
  });
}

export async function consumir(codigo: string, cantidad: number): Promise<{ ok: true } | { ok: false; motivo: string }> {
  // Lectura+escritura dentro de una transacción Dexie: dos consumos concurrentes del mismo
  // repuesto no deben pisarse uno al otro (perder una actualización).
  return db.transaction("rw", db.stockMovilLocal, async () => {
    const item = await db.stockMovilLocal.get(codigo);
    if (!item) return { ok: false, motivo: "No hay stock móvil cargado para ese repuesto" };
    if (item.cantidad_consumida + cantidad > item.cantidad_cargada) {
      return { ok: false, motivo: "Stock móvil insuficiente" };
    }
    await db.stockMovilLocal.update(codigo, { cantidad_consumida: item.cantidad_consumida + cantidad });
    return { ok: true };
  });
}
