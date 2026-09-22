import { ApiError, apiFetch } from "../api/client";
import { db, type OrdenLocal } from "./dexie";

/** El propio ordenesLocal filtrado por estado_sync='pendiente' es el Outbox: sin cola aparte. */
export async function procesarOutbox(): Promise<void> {
  const pendientes = await db.ordenesLocal.where("estado_sync").equals("pendiente").sortBy("creado_en_local");
  for (const orden of pendientes) {
    await sincronizarUna(orden); // secuencial: nunca Promise.all — el hash encadenado depende del orden de llegada
  }
}

function aPayloadDeSincronizacion(orden: OrdenLocal) {
  // Solo los campos que OrdenSincronizarIn espera en el backend — nunca los campos
  // de bookkeeping local (estado_sync, error_detalle, creado_en_local, intentos_sync).
  const { estado_sync: _es, error_detalle: _ed, creado_en_local: _cl, intentos_sync: _is, ...payload } = orden;
  return payload;
}

async function sincronizarUna(orden: OrdenLocal): Promise<void> {
  await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizando" });
  try {
    await apiFetch("/ordenes", { method: "POST", body: aPayloadDeSincronizacion(orden) });
    await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizada" });
  } catch (e) {
    if (e instanceof ApiError && e.status !== 0) {
      // Error de negocio (4xx del backend): no se pierde, pero tampoco se reintenta sola.
      await db.ordenesLocal.update(orden.id, { estado_sync: "error", error_detalle: e.message });
    } else {
      // Error de red (status 0): vuelve a pendiente para el proximo ciclo.
      await db.ordenesLocal.update(orden.id, { estado_sync: "pendiente", intentos_sync: orden.intentos_sync + 1 });
    }
  }
}
