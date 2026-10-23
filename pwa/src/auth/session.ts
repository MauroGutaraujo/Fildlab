// Sesión de turno: se guarda en IndexedDB (tabla `sesion` de Dexie), no en sessionStorage,
// para que sobreviva reinicios de la PWA instalada durante un turno de campo de 12h.
import { db } from "../db/dexie";

export const EVENTO_SESION = "fildlab:sesion";

function notificarSesion() {
  window.dispatchEvent(new Event(EVENTO_SESION));
}

export async function guardarSesionTurno(token: string): Promise<void> {
  await db.sesion.put({ id: "actual", token, guardado_en: new Date().toISOString() });
  notificarSesion();
}

export async function obtenerToken(): Promise<string | null> {
  const sesion = await db.sesion.get("actual");
  return sesion?.token ?? null;
}

export async function cerrarSesion(): Promise<void> {
  await db.sesion.delete("actual");
  notificarSesion();
}

/** Lee el `sub` (id de usuario) del JWT ya guardado, sin llamada de red adicional.
 * No valida la firma — la validación real la hace el backend en cada request. */
export function decodeTecnicoId(token: string): number | null {
  return leerClaims(token)?.tecnicoId ?? null;
}

function leerClaims(token: string): { tecnicoId: number; exp: number } | null {
  try {
    const partes = token.split(".");
    if (partes.length !== 3 || partes.some((p) => !/^[A-Za-z0-9_-]+$/.test(p))) return null;
    const base64 = (parte: string) => atob(parte.replace(/-/g, "+").replace(/_/g, "/"));
    const decodificar = (parte: string) => JSON.parse(base64(parte));
    base64(partes[2]); // Sólo estructura; la firma la verifica el servidor.
    const header = decodificar(partes[0]);
    const payload = decodificar(partes[1]);
    if (!header || typeof header.alg !== "string" || header.alg.toLowerCase() === "none") return null;
    if (!payload || typeof payload.sub !== "string" || !/^[1-9]\d*$/.test(payload.sub)) return null;
    const tecnicoId = Number(payload.sub);
    if (!Number.isSafeInteger(tecnicoId) || !Number.isSafeInteger(payload.exp) || payload.exp <= 0) return null;
    return { tecnicoId, exp: payload.exp };
  } catch {
    return null;
  }
}

export function tokenVigente(token: string): boolean {
  const claims = leerClaims(token);
  return claims !== null && claims.exp > Date.now() / 1000;
}

export async function obtenerSesionTransmisible() {
  const sesion = await db.sesion.get("actual");
  if (!sesion || sesion.requiere_renovacion || !tokenVigente(sesion.token)) return null;
  return { ...sesion, tecnicoId: decodeTecnicoId(sesion.token)! };
}

/** Un 401 de una petición anterior nunca invalida una sesión recién iniciada. */
export async function solicitarRenovacion(token: string, guardadoEn: string): Promise<void> {
  let cambio = false;
  await db.transaction("rw", db.sesion, async () => {
    const sesion = await db.sesion.get("actual");
    if (sesion?.token === token && sesion.guardado_en === guardadoEn) {
      await db.sesion.update("actual", { requiere_renovacion: true });
      cambio = true;
    }
  });
  if (cambio) notificarSesion();
}
