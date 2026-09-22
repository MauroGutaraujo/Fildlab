import { describe, expect, it, beforeEach } from "vitest";
import { db } from "./dexie";

describe("esquema Dexie", () => {
  beforeEach(async () => {
    await db.ordenesLocal.clear();
  });

  it("guarda y recupera una orden local con estado_sync por defecto", async () => {
    await db.ordenesLocal.add({
      id: "11111111-1111-1111-1111-111111111111",
      contrato_id: 1,
      equipo_serie: "RO-1",
      tecnico_id: 2,
      tipo_intervencion: "PREVENTIVO",
      fecha_creacion_cliente: "2026-03-01T10:00:00Z",
      lecturas_agua: {
        tds_entrada_ppm: 350, tds_post_membrana_ppm: 8, tds_producto_final_ppm: 5,
        ph: 7, conductividad_us_cm: 15, resistividad_mohm_cm: 1.2,
        litros_consumidos_red: 500, litros_agua_pura: 420,
      },
      firma_base64: "AAAA",
      gps_latitud: -8.1116,
      gps_longitud: -79.0288,
      repuestos_consumidos: [],
      estado_sync: "pendiente",
      creado_en_local: "2026-03-01T10:00:00Z",
      intentos_sync: 0,
    });
    const guardada = await db.ordenesLocal.get("11111111-1111-1111-1111-111111111111");
    expect(guardada?.estado_sync).toBe("pendiente");
  });

  it("permite consultar ordenesLocal por estado_sync (el Outbox)", async () => {
    const pendientes = await db.ordenesLocal.where("estado_sync").equals("pendiente").toArray();
    expect(Array.isArray(pendientes)).toBe(true);
  });
});
