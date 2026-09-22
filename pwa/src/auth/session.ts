// Sesión de turno: se guarda en IndexedDB (tabla `sesion` de Dexie), no en sessionStorage,
// para que sobreviva reinicios de la PWA instalada durante un turno de campo de 12h.
import { db } from "../db/dexie";

export async function guardarSesionTurno(token: string): Promise<void> {
  await db.sesion.put({ id: "actual", token, guardado_en: new Date().toISOString() });
}

export async function obtenerToken(): Promise<string | null> {
  const sesion = await db.sesion.get("actual");
  return sesion?.token ?? null;
}

export async function cerrarSesion(): Promise<void> {
  await db.sesion.delete("actual");
}
