import { apiFetch } from "../api/client";
import { db, type CatalogoItem } from "./dexie";

type ClienteApi = { ruc: string };
type EquipoApi = { serie: string };
type ContratoApi = { id: number };

/** Refresca el catálogo local cuando hay red. Si una o más llamadas fallan (sin conexión),
 * el catálogo previo queda intacto — nunca se borra por falta de red. */
export async function refrescarCatalogo(): Promise<void> {
  const [clientes, equipos, contratos] = await Promise.allSettled([
    apiFetch<ClienteApi[]>("/clientes"),
    apiFetch<EquipoApi[]>("/equipos"),
    apiFetch<ContratoApi[]>("/contratos"),
  ]);

  const items: CatalogoItem[] = [];
  const ahora = new Date().toISOString();
  if (clientes.status === "fulfilled") {
    items.push(...clientes.value.map((c) => ({ id: c.ruc, tipo: "cliente" as const, datos: c, actualizado_en: ahora })));
  }
  if (equipos.status === "fulfilled") {
    items.push(...equipos.value.map((e) => ({ id: e.serie, tipo: "equipo" as const, datos: e, actualizado_en: ahora })));
  }
  if (contratos.status === "fulfilled") {
    items.push(
      ...contratos.value.map((c) => ({ id: String(c.id), tipo: "contrato" as const, datos: c, actualizado_en: ahora })),
    );
  }
  if (items.length > 0) await db.catalogoLocal.bulkPut(items);
}

export async function buscarEquipos(query: string): Promise<CatalogoItem[]> {
  const equipos = await db.catalogoLocal.where("tipo").equals("equipo").toArray();
  const q = query.trim().toLowerCase();
  return q ? equipos.filter((e) => e.id.toLowerCase().includes(q)) : equipos;
}
