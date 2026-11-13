import { apiFetch } from "../api/client";
import { db, type CatalogoItem } from "./dexie";

type ClienteApi = { ruc: string };
type EquipoApi = { serie: string };
type ContratoApi = { id: number };
export type RepuestoApi = { codigo: string; descripcion: string };

/** Refresca el catálogo local cuando hay red. Si una o más llamadas fallan (sin conexión),
 * el catálogo previo queda intacto — nunca se borra por falta de red. */
export async function refrescarCatalogo(): Promise<void> {
  const [clientes, equipos, contratos, repuestos] = await Promise.allSettled([
    apiFetch<ClienteApi[]>("/clientes"),
    apiFetch<EquipoApi[]>("/equipos"),
    apiFetch<ContratoApi[]>("/contratos"),
    apiFetch<RepuestoApi[]>("/repuestos"),
  ]);

  const items: CatalogoItem[] = [];
  const ahora = new Date().toISOString();
  // Array.isArray: una respuesta inesperada (backend caído devolviendo HTML de error con
  // status 200 detrás de un proxy, por ejemplo) no debe tumbar la sincronización entera.
  if (clientes.status === "fulfilled" && Array.isArray(clientes.value)) {
    items.push(...clientes.value.map((c) => ({ id: c.ruc, tipo: "cliente" as const, datos: c, actualizado_en: ahora })));
  }
  if (equipos.status === "fulfilled" && Array.isArray(equipos.value)) {
    items.push(...equipos.value.map((e) => ({ id: e.serie, tipo: "equipo" as const, datos: e, actualizado_en: ahora })));
  }
  if (contratos.status === "fulfilled" && Array.isArray(contratos.value)) {
    items.push(
      ...contratos.value.map((c) => ({ id: String(c.id), tipo: "contrato" as const, datos: c, actualizado_en: ahora })),
    );
  }
  if (repuestos.status === "fulfilled" && Array.isArray(repuestos.value)) {
    items.push(...repuestos.value.map((r) => ({ id: r.codigo, tipo: "repuesto" as const, datos: r, actualizado_en: ahora })));
  }
  if (items.length > 0) await db.catalogoLocal.bulkPut(items);
}

export async function buscarEquipos(query: string): Promise<CatalogoItem[]> {
  const equipos = await db.catalogoLocal.where("tipo").equals("equipo").toArray();
  const q = query.trim().toLowerCase();
  return q ? equipos.filter((e) => e.id.toLowerCase().includes(q)) : equipos;
}

export async function obtenerRepuestosCatalogo(): Promise<RepuestoApi[]> {
  const items = await db.catalogoLocal.where("tipo").equals("repuesto").toArray();
  return items.map((i) => i.datos as RepuestoApi);
}
