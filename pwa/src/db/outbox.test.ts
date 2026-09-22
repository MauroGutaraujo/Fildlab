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

  it("recupera ordenes atrapadas en 'sincronizando' (proceso muerto a mitad de sync) antes de procesar", async () => {
    // Si el dispositivo se apaga/recarga entre marcar "sincronizando" y recibir la respuesta,
    // sin esto la orden queda huerfana para siempre (viola RNF-04: cero perdida).
    await db.ordenesLocal.add({ ...ORDEN_BASE, id: "55555555-5555-5555-5555-555555555555", estado_sync: "sincronizando" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "1" }), { status: 201 }));
    await procesarOutbox();
    expect((await db.ordenesLocal.get("55555555-5555-5555-5555-555555555555"))?.estado_sync).toBe("sincronizada");
  });

  it("un 409 por carrera (la orden SI existe en el servidor) se reconcilia como sincronizada, no como error", async () => {
    // Dos POST del mismo id casi simultaneos: el que pierde la carrera recibe 409 de
    // IntegrityError, pero la orden SI se creo (la gano la otra peticion) — no es un
    // fallo de negocio real, y no debe marcarse como perdida.
    await agregarPendiente("66666666-6666-6666-6666-666666666666");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if ((init?.method ?? "GET") === "POST") {
        return new Response(JSON.stringify({ detail: "El registro ya existe o entra en conflicto" }), { status: 409 });
      }
      // GET /ordenes/{id} de reconciliacion: la orden si existe en el servidor.
      expect(String(input)).toContain("66666666-6666-6666-6666-666666666666");
      return new Response(JSON.stringify({ id: "66666666-6666-6666-6666-666666666666", estado: "SINCRONIZADA" }), { status: 200 });
    });
    await procesarOutbox();
    expect((await db.ordenesLocal.get("66666666-6666-6666-6666-666666666666"))?.estado_sync).toBe("sincronizada");
  });

  it("un 409 real (la orden NO existe: fallo de negocio, ej. stock insuficiente) se marca como error", async () => {
    await agregarPendiente("77777777-7777-7777-7777-777777777777");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if ((init?.method ?? "GET") === "POST") {
        return new Response(JSON.stringify({ detail: "FILT-05: stock 2, se piden 5" }), { status: 409 });
      }
      return new Response(JSON.stringify({ detail: "Orden no encontrada" }), { status: 404 });
    });
    await procesarOutbox();
    const o = await db.ordenesLocal.get("77777777-7777-7777-7777-777777777777");
    expect(o?.estado_sync).toBe("error");
    expect(o?.error_detalle).toContain("stock 2, se piden 5");
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
