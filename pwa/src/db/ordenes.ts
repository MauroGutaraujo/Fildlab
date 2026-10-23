import { db, type BorradorOrden, type LecturasAgua } from "./dexie";
import { CAMPOS_LECTURA_ORDEN, errorLectura } from "../lib/validators";
import { consumir } from "./stock";
import { errorTiemposServicio } from "../lib/tiemposServicio";

const CONFLICTO = "El borrador cambió en otra pestaña. Vuelve a abrir el equipo para recuperar la versión guardada";
export class ConflictoBorradorError extends Error {}

function mismaRevision(actual: BorradorOrden | undefined, copia: BorradorOrden): void {
  if (!actual || actual.id !== copia.id || actual.revision !== copia.revision) throw new ConflictoBorradorError(CONFLICTO);
}

export async function guardarBorrador(borrador: BorradorOrden): Promise<BorradorOrden> {
  return db.transaction("rw", db.borradoresOrden, db.ordenesLocal, async () => {
    if (await db.ordenesLocal.get(borrador.id)) throw new ConflictoBorradorError("La orden ya está cerrada en otra pestaña");
    const existente = await db.borradoresOrden.get([borrador.tecnico_id, borrador.equipo_serie]);
    mismaRevision(existente, borrador);
    const guardado = { ...borrador, revision: borrador.revision + 1 };
    await db.borradoresOrden.put(guardado);
    return guardado;
  });
}

export async function abrirBorrador(tecnicoId: number, serie: string, contratoId: number): Promise<BorradorOrden> {
  return db.transaction("rw", db.borradoresOrden, async () => {
    const existente = await db.borradoresOrden.get([tecnicoId, serie]);
    if (existente) return existente;
    const nuevo: BorradorOrden = {
      id: crypto.randomUUID(), revision: 0, tecnico_id: tecnicoId, equipo_serie: serie, contrato_id: contratoId,
      tipo_intervencion: "PREVENTIVO", lecturas: Object.fromEntries(CAMPOS_LECTURA_ORDEN.map((c) => [c, ""])) as BorradorOrden["lecturas"],
      firma_base64: null, gps_latitud: null, gps_longitud: null,
      repuestos_consumidos: [], creado_en_local: new Date().toISOString(),
    };
    await db.borradoresOrden.add(nuevo);
    return nuevo;
  });
}

export async function descartarBorrador(borrador: BorradorOrden): Promise<void> {
  await db.transaction("rw", db.borradoresOrden, async () => {
    const clave: [number, string] = [borrador.tecnico_id, borrador.equipo_serie];
    mismaRevision(await db.borradoresOrden.get(clave), borrador);
    await db.borradoresOrden.delete(clave);
  });
}

export async function cerrarBorrador(borrador: BorradorOrden): Promise<void> {
  const ahora = new Date().toISOString();
  const errorTiempos = errorTiemposServicio(borrador.fecha_solicitud, borrador.fecha_primera_atencion, ahora);
  if (errorTiempos) throw new Error(errorTiempos);
  if (CAMPOS_LECTURA_ORDEN.some((c) => errorLectura(c, borrador.lecturas[c]) !== null)) {
    throw new Error("Completa las lecturas válidas antes de cerrar");
  }
  const { gps_latitud: lat, gps_longitud: lng, firma_base64: firma } = borrador;
  if (!firma?.trim() || lat === null || lng === null || !Number.isFinite(lat) || !Number.isFinite(lng)
      || Math.abs(lat) > 90 || Math.abs(lng) > 180) throw new Error("Completa firma y ubicación antes de cerrar");
  await db.transaction("rw", db.ordenesLocal, db.stockPorTecnico, db.borradoresOrden, async () => {
    // La transacción serializa cierres incluso desde dos pestañas.
    if (await db.ordenesLocal.get(borrador.id)) return;
    const guardado = await db.borradoresOrden.get([borrador.tecnico_id, borrador.equipo_serie]);
    mismaRevision(guardado, borrador);
    for (const item of borrador.repuestos_consumidos) {
      const r = await consumir(item.repuesto_codigo, item.cantidad, borrador.tecnico_id);
      if (!r.ok) throw new Error(r.motivo);
    }
    await db.ordenesLocal.add({
      id: borrador.id, tecnico_id: borrador.tecnico_id, equipo_serie: borrador.equipo_serie,
      contrato_id: borrador.contrato_id, tipo_intervencion: borrador.tipo_intervencion,
      lecturas_agua: Object.fromEntries(CAMPOS_LECTURA_ORDEN.map((c) => [c, Number(borrador.lecturas[c])])) as unknown as LecturasAgua,
      firma_base64: firma, gps_latitud: lat, gps_longitud: lng,
      repuestos_consumidos: borrador.repuestos_consumidos,
      fecha_creacion_cliente: ahora, creado_en_local: borrador.creado_en_local,
      fecha_solicitud: borrador.fecha_solicitud ? new Date(borrador.fecha_solicitud).toISOString() : undefined,
      fecha_primera_atencion: borrador.fecha_primera_atencion ? new Date(borrador.fecha_primera_atencion).toISOString() : undefined,
      estado_sync: "pendiente", intentos_sync: 0,
    });
    await db.borradoresOrden.delete([borrador.tecnico_id, borrador.equipo_serie]);
  });
}
