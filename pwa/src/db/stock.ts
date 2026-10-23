import { db, type StockTecnicoItem } from "./dexie";

function validarCantidad(codigo: string, cantidad: number, tecnicoId: number): void {
  if (!codigo.trim() || !Number.isSafeInteger(cantidad) || cantidad <= 0 || !Number.isSafeInteger(tecnicoId) || tecnicoId <= 0) {
    throw new Error("Indica un código, una cantidad entera positiva y un técnico válido");
  }
}

function validarSaldo(item: StockTecnicoItem): void {
  if (![item.cantidad_cargada, item.cantidad_consumida].every((n) => Number.isSafeInteger(n) && n >= 0)
      || item.cantidad_consumida > item.cantidad_cargada) {
    throw new Error("Saldo móvil inválido. Solicita su revisión antes de registrar consumos");
  }
}

export async function cargarStockTurno(
  items: { repuesto_codigo: string; cantidad: number }[], turnoId: string, tecnicoId: number,
): Promise<void> {
  for (const i of items) validarCantidad(i.repuesto_codigo, i.cantidad, tecnicoId);
  if (!turnoId.trim()) throw new Error("El turno es obligatorio");
  await db.transaction("rw", db.stockPorTecnico, async () => {
    for (const i of items) {
      const codigo = i.repuesto_codigo.trim();
      const previo = await db.stockPorTecnico.get([tecnicoId, codigo]);
      if (previo) validarSaldo(previo);
      const cargada = (previo?.cantidad_cargada ?? 0) + i.cantidad;
      if (!Number.isSafeInteger(cargada)) throw new Error("La cantidad supera el límite permitido");
      await db.stockPorTecnico.put({
        tecnico_id: tecnicoId, repuesto_codigo: codigo, cantidad_cargada: cargada,
        cantidad_consumida: previo?.cantidad_consumida ?? 0, turno_id: turnoId,
      });
    }
  });
}

export async function comprobarDisponibilidad(codigo: string, cantidad: number, tecnicoId: number): Promise<void> {
  validarCantidad(codigo, cantidad, tecnicoId);
  const item = await db.stockPorTecnico.get([tecnicoId, codigo.trim()]);
  if (!item) throw new Error("No hay stock móvil cargado para ese repuesto");
  validarSaldo(item);
  if (cantidad > item.cantidad_cargada - item.cantidad_consumida) throw new Error("Stock móvil insuficiente");
}

export async function consumir(codigo: string, cantidad: number, tecnicoId: number): Promise<{ ok: true } | { ok: false; motivo: string }> {
  return db.transaction("rw", db.stockPorTecnico, async () => {
    try {
      await comprobarDisponibilidad(codigo, cantidad, tecnicoId);
    } catch (error) {
      return { ok: false, motivo: error instanceof Error ? error.message : "No se pudo verificar el stock" };
    }
    await db.stockPorTecnico.where(":id").equals([tecnicoId, codigo.trim()]).modify((item) => {
      item.cantidad_consumida += cantidad;
    });
    return { ok: true };
  });
}
