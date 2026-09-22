import { describe, expect, it, vi, beforeEach } from "vitest";
import { db } from "./dexie";
import { refrescarCatalogo, buscarEquipos } from "./catalogo";

function mockApi(clientes: unknown[], equipos: unknown[], contratos: unknown[]) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const body = url.includes("/clientes") ? clientes : url.includes("/equipos") ? equipos : contratos;
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
}

describe("catalogo local", () => {
  beforeEach(async () => {
    await db.catalogoLocal.clear();
  });

  it("refrescar puebla clientes, equipos y contratos", async () => {
    mockApi([{ ruc: "20612493821" }], [{ serie: "RO-1" }], [{ id: 1 }]);
    await refrescarCatalogo();
    expect((await db.catalogoLocal.where("tipo").equals("equipo").toArray())[0].datos).toEqual({ serie: "RO-1" });
  });

  it("buscarEquipos funciona sin red, leyendo de Dexie", async () => {
    await db.catalogoLocal.add({ id: "RO-1", tipo: "equipo", datos: { serie: "RO-1" }, actualizado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("sin red"));
    const r = await buscarEquipos("RO");
    expect(r).toHaveLength(1);
  });

  it("si falla la red, refrescarCatalogo no borra lo que ya habia", async () => {
    await db.catalogoLocal.add({ id: "RO-1", tipo: "equipo", datos: { serie: "RO-1" }, actualizado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("sin red"));
    await refrescarCatalogo();
    expect(await db.catalogoLocal.get("RO-1")).toBeDefined();
  });
});
