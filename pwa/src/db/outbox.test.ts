import { describe, expect, it, vi, beforeEach } from "vitest";
import { db } from "./dexie";
import { procesarOutbox } from "./outbox";

const ORDEN_BASE = {
  contrato_id: 1, equipo_serie: "RO-1", tecnico_id: 1, tipo_intervencion: "PREVENTIVO",
  fecha_creacion_cliente: "2026-03-01T10:00:00Z",
  lecturas_agua: { tds_entrada_ppm: 1, tds_post_membrana_ppm: 1, tds_producto_final_ppm: 1, ph: 7,
                   conductividad_us_cm: 1, resistividad_mohm_cm: 1, litros_consumidos_red: 1, litros_agua_pura: 1 },
  firma_base64: "AAAA", gps_latitud: -8, gps_longitud: -79, repuestos_consumidos: [],
  creado_en_local: "2026-03-01T10:00:00Z", intentos_sync: 0,
};

async function agregarPendiente(id: string, over: Partial<typeof ORDEN_BASE> = {}) {
  await db.ordenesLocal.add({ ...ORDEN_BASE, ...over, id, estado_sync: "pendiente" });
}

describe("procesarOutbox", () => {
  beforeEach(async () => {
    await db.ordenesLocal.clear();
  });

  it("marca sincronizada en exito", async () => {
    await agregarPendiente("11111111-1111-1111-1111-111111111111");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "1" }), { status: 201 }));
    await procesarOutbox();
    expect((await db.ordenesLocal.get("11111111-1111-1111-1111-111111111111"))?.estado_sync).toBe("sincronizada");
  });

  it("marca error en fallo de negocio (409) y no reintenta sola", async () => {
    await agregarPendiente("22222222-2222-2222-2222-222222222222");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "stock insuficiente" }), { status: 409 }),
    );
    await procesarOutbox();
    const o = await db.ordenesLocal.get("22222222-2222-2222-2222-222222222222");
    expect(o?.estado_sync).toBe("error");
    expect(o?.error_detalle).toContain("stock insuficiente");
  });

  it("deja pendiente en fallo de red (se reintenta despues)", async () => {
    await agregarPendiente("33333333-3333-3333-3333-333333333333");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("sin red"));
    await procesarOutbox();
    expect((await db.ordenesLocal.get("33333333-3333-3333-3333-333333333333"))?.estado_sync).toBe("pendiente");
  });

  it("procesa en orden por creado_en_local, no en paralelo", async () => {
    await db.ordenesLocal.bulkAdd([
      { ...ORDEN_BASE, id: "a", creado_en_local: "2026-03-01T10:02:00Z", estado_sync: "pendiente" },
      { ...ORDEN_BASE, id: "b", creado_en_local: "2026-03-01T10:01:00Z", estado_sync: "pendiente" },
    ]);
    const orden: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, init) => {
      orden.push(JSON.parse((init as RequestInit).body as string).id);
      return new Response(JSON.stringify({ id: "x" }), { status: 201 });
    });
    await procesarOutbox();
    expect(orden).toEqual(["b", "a"]); // b es mas antigua, va primero
  });

  it("no envia campos de bookkeeping local (estado_sync, error_detalle, etc.) al backend", async () => {
    await agregarPendiente("44444444-4444-4444-4444-444444444444");
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "1" }), { status: 201 }));
    await procesarOutbox();
    const enviado = JSON.parse((f.mock.calls[0][1] as RequestInit).body as string);
    expect(enviado).not.toHaveProperty("estado_sync");
    expect(enviado).not.toHaveProperty("error_detalle");
    expect(enviado).not.toHaveProperty("creado_en_local");
    expect(enviado).not.toHaveProperty("intentos_sync");
    expect(enviado.id).toBe("44444444-4444-4444-4444-444444444444");
  });
});
