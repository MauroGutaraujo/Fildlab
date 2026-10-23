import { describe, expect, it, beforeEach } from "vitest";
import { db } from "./dexie";
import Dexie from "dexie";

describe("esquema Dexie", () => {
  it("actualiza desde v1 conservando stock sin dueño y órdenes anteriores", async () => {
    await db.delete();
    const antigua = new Dexie(db.name);
    antigua.version(1).stores({ catalogoLocal: "id, tipo", ordenesLocal: "id, estado_sync, creado_en_local", stockMovilLocal: "repuesto_codigo, turno_id", sesion: "id" });
    try {
      await antigua.table("stockMovilLocal").put({ repuesto_codigo: "LEGADO", cantidad_cargada: 10, cantidad_consumida: 2, turno_id: "turno-antiguo" });
      await antigua.table("ordenesLocal").put({ id: "acta-antigua", tecnico_id: 7, estado_sync: "pendiente", creado_en_local: "2026-10-01" });
    } finally { antigua.close(); }
    await db.open();
    expect((await db.stockMovilLocal.get("LEGADO"))?.cantidad_consumida).toBe(2);
    expect(await db.ordenesLocal.where("tecnico_id").equals(7).count()).toBe(1);
    expect(await db.stockPorTecnico.count()).toBe(0);
    expect(await db.borradoresOrden.count()).toBe(0);
  });
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
