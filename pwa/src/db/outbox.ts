import { ApiError, apiFetch } from "../api/client";
import { obtenerSesionTransmisible, solicitarRenovacion } from "../auth/session";
import { db, type OrdenLocal } from "./dexie";

export const EVENTO_OUTBOX = "fildlab:outbox";

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
    window.dispatchEvent(new Event(EVENTO_OUTBOX));
  }
}

async function ejecutar(): Promise<void> {
  const sesion = await obtenerSesionTransmisible();
  if (!sesion) return;
  // Una orden puede quedar en "sincronizando" si el proceso murió entre marcarla y recibir
  // la respuesta (batería, recarga del service worker, cierre de la PWA). Es seguro reintentarla
  // porque el backend es idempotente por id (nunca duplica si ya llegó).
  await db.ordenesLocal.where("tecnico_id").equals(sesion.tecnicoId)
    .filter((orden) => orden.estado_sync === "sincronizando" || esErrorDeAutenticacion(orden))
    .modify({ estado_sync: "pendiente", error_detalle: undefined, error_status: undefined });

  const pendientes = await db.ordenesLocal.where("tecnico_id").equals(sesion.tecnicoId)
    .filter((orden) => orden.estado_sync === "pendiente").sortBy("creado_en_local");
  for (const orden of pendientes) {
    if (!(await mismaSesion(sesion))) break;
    if (!(await sincronizarUna(orden, sesion))) break;
  }
}

type SesionTransmisible = NonNullable<Awaited<ReturnType<typeof obtenerSesionTransmisible>>>;

async function mismaSesion(sesion: SesionTransmisible): Promise<boolean> {
  const actual = await obtenerSesionTransmisible();
  return actual?.token === sesion.token && actual.guardado_en === sesion.guardado_en;
}

function esErrorDeAutenticacion(orden: OrdenLocal): boolean {
  if (orden.estado_sync !== "error") return false;
  return orden.error_status === 401 || (orden.error_status === undefined &&
    ["No autenticado", "Token inválido", "Error 401"].includes(orden.error_detalle ?? ""));
}

function aPayloadDeSincronizacion(orden: OrdenLocal) {
  // Solo los campos que OrdenSincronizarIn espera en el backend — nunca los campos
  // de bookkeeping local (estado_sync, error_detalle, creado_en_local, intentos_sync).
  const { estado_sync: _es, error_detalle: _ed, error_status: _st, creado_en_local: _cl, intentos_sync: _is, ...payload } = orden;
  return payload;
}

async function ordenYaExisteEnServidor(id: string, sesion: SesionTransmisible): Promise<boolean> {
  if (!(await mismaSesion(sesion))) return false;
  try {
    await apiFetch(`/ordenes/${id}`, { token: sesion.token });
    return true;
  } catch (e) {
    if (!(e instanceof ApiError) || e.status === 401 || esReintentable(e.status)) throw e;
    return false;
  }
}

async function sincronizarUna(orden: OrdenLocal, sesion: SesionTransmisible): Promise<boolean> {
  await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizando" });
  if (!(await mismaSesion(sesion))) {
    await db.ordenesLocal.update(orden.id, { estado_sync: "pendiente" });
    return false;
  }
  try {
    try {
      await apiFetch("/ordenes", { method: "POST", body: aPayloadDeSincronizacion(orden), token: sesion.token });
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 409 && await ordenYaExisteEnServidor(orden.id, sesion))) throw e;
    }
    await db.ordenesLocal.update(orden.id, { estado_sync: "sincronizada", error_detalle: undefined, error_status: undefined });
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      await db.ordenesLocal.update(orden.id, { estado_sync: "pendiente", error_detalle: "Renueva la sesión para sincronizar", error_status: 401 });
      await solicitarRenovacion(sesion.token, sesion.guardado_en);
      return false;
    } else if (!(await mismaSesion(sesion))) {
      await db.ordenesLocal.update(orden.id, { estado_sync: "pendiente" });
      return false;
    } else if (e instanceof ApiError && !esReintentable(e.status)) {
      // Error de negocio permanente (422/404/403, o 409 real de stock insuficiente): no se
      // pierde, pero tampoco se reintenta sola — el técnico o Gerencia deciden.
      await db.ordenesLocal.update(orden.id, { estado_sync: "error", error_detalle: e.message, error_status: e.status });
    } else {
      // Red caída o reconciliación aún no verificable: conservar para el próximo ciclo.
      // vuelve a pendiente para el proximo ciclo.
      await db.ordenesLocal.update(orden.id, { estado_sync: "pendiente", intentos_sync: orden.intentos_sync + 1 });
    }
  }
  return true;
}
