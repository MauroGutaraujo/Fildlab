// Placeholder minimo para que api/client.ts pueda importar obtenerToken antes de la Tarea 5
// (que construye la sesion de turno completa en IndexedDB). Se reemplaza en la Tarea 5.
import { db } from "../db/dexie";

export async function obtenerToken(): Promise<string | null> {
  const sesion = await db.sesion.get("actual");
  return sesion?.token ?? null;
}
