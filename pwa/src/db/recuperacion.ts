import { decodeTecnicoId, obtenerSesionTransmisible, obtenerToken } from "../auth/session";
import { db, type OrdenLocal } from "./dexie";
import { procesarOutbox } from "./outbox";

export function admiteReintentoManual(orden: OrdenLocal): boolean {
  return orden.estado_sync === "error" && [403, 404, 409].includes(orden.error_status ?? 0);
}

async function obtenerOrdenPropia(id: string, tecnicoId: number, accion: "exportar" | "enviar"): Promise<OrdenLocal> {
  const orden = await db.ordenesLocal.get(id);
  // El rescate local admite la identidad guardada aunque el turno haya vencido; enviar sí exige vigencia.
  const propietario = accion === "exportar"
    ? decodeTecnicoId((await obtenerToken()) ?? "")
    : (await obtenerSesionTransmisible())?.tecnicoId;
  if (propietario !== tecnicoId) throw new Error(accion === "exportar"
    ? "Se necesita la sesión guardada del propietario para exportar"
    : "Renueva la sesión del propietario para continuar");
  if (!orden || orden.tecnico_id !== tecnicoId) throw new Error("La orden no pertenece al propietario de la sesión");
  return orden;
}

export async function exportarOrden(id: string, tecnicoId: number): Promise<string> {
  return db.transaction("r", db.ordenesLocal, db.sesion, async () => {
    const orden = await obtenerOrdenPropia(id, tecnicoId, "exportar");
    // Sólo la fila original de esta orden. Nunca se exporta la tabla de sesión ni el catálogo.
    return JSON.stringify(orden, null, 2);
  });
}

export async function reintentarOrden(id: string, tecnicoId: number): Promise<void> {
  await db.transaction("rw", db.ordenesLocal, db.sesion, async () => {
    // Sesión y propietario se vuelven a leer dentro de la misma transacción que cambia el estado.
    const orden = await obtenerOrdenPropia(id, tecnicoId, "enviar");
    if (!admiteReintentoManual(orden)) throw new Error("Esta orden requiere revisión. Exporta el JSON original para Gerencia");
    await db.ordenesLocal.update(id, { estado_sync: "pendiente", error_detalle: undefined, error_status: undefined });
  });
  await procesarOutbox();
}
