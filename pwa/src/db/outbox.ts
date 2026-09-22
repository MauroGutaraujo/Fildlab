import { ApiError, apiFetch } from "../api/client";
import { db, type OrdenLocal } from "./dexie";

/** Un status del backend/red que amerita reintento automático, no un error terminal.
 * 0 = fallo de red/timeout; 5xx = servidor caído o en cold start (RNF-01); 408/429 = reintentable. */
function esReintentable(status: number): boolean {
  return status === 0 || status >= 500 || status === 408 || status === 429;
}

let enCurso: Promise<void> | null = null;

/** El propio ordenesLocal filtrado por estado_sync='pendiente' es el Outbox: sin cola aparte.
 * No reentrante: si ya hay una pasada en curso (listener 'online' + intervalo de respaldo +
 * botón manual pueden dispararse a la vez), se devuelve la misma promesa en vez de solapar
 * dos POST del mismo id (rompería el orden secuencial que protege el encadenado de hash). */
export async function procesarOutbox(): Promise<void> {
  if (enCurso) return enCurso;
  enCurso = ejecutar();
  try {
    await enCurso;
  } finally {
    enCurso = null;
  }
}

async function ejecutar(): Promise<void> {
  // Una orden puede quedar en "sincronizando" si el proceso murió entre marcarla y recibir
  // la respuesta (batería, recarga del service worker, cierre de la PWA). Es seguro reintentarla
  // porque el backend es idempotente por id (nunca duplica si ya llegó).
  await db.ordenesLocal.where("estado_sync").equals("sincronizando").modify({ estado_sync: "pendiente" });

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

async function ordenYaExisteEnServidor(id: string): Promise<boolean> {
  try {
    await apiFetch(`/ordenes/${id}`);
    return true;
  } catch {
    return false;
  }
}

async function sincronizarUna(orden: OrdenLocal): Promise<void> {
  await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizando" });
  try {
    await apiFetch("/ordenes", { method: "POST", body: aPayloadDeSincronizacion(orden) });
    await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizada" });
  } catch (e) {
    if (e instanceof ApiError && e.status === 409 && (await ordenYaExisteEnServidor(orden.id))) {
      // Carrera real (Review Focus 1): dos POST del mismo id, este perdió con un 409 de
      // IntegrityError, pero la orden SÍ existe — la creó la otra petición. No es un fallo.
      await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizada" });
    } else if (e instanceof ApiError && !esReintentable(e.status)) {
      // Error de negocio permanente (422/404/403, o 409 real de stock insuficiente): no se
      // pierde, pero tampoco se reintenta sola — el técnico o Gerencia deciden.
      await db.ordenesLocal.update(orden.id, { estado_sync: "error", error_detalle: e.message });
    } else {
      // Red caída, cold start del backend (RNF-01), o un 409 de carrera (Review Focus 1):
      // vuelve a pendiente para el proximo ciclo.
      await db.ordenesLocal.update(orden.id, { estado_sync: "pendiente", intentos_sync: orden.intentos_sync + 1 });
    }
  }
}
