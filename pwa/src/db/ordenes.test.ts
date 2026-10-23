import { describe, expect, it, vi } from "vitest";
import { db, type BorradorOrden } from "./dexie";
import { cargarStockTurno } from "./stock";
import { cerrarBorrador, guardarBorrador, descartarBorrador, abrirBorrador } from "./ordenes";

const borrador = (): BorradorOrden => ({
  id: "orden-estable", revision: 0, tecnico_id: 2, equipo_serie: "RO-1", contrato_id: 1, tipo_intervencion: "PREVENTIVO",
  lecturas: { tds_entrada_ppm: "350", tds_post_membrana_ppm: "8", tds_producto_final_ppm: "5", ph: "7",
    conductividad_us_cm: "15", resistividad_mohm_cm: "1.2", litros_consumidos_red: "500", litros_agua_pura: "420" },
  firma_base64: "data:image/png;base64,FIRMA", gps_latitud: -8, gps_longitud: -79,
  repuestos_consumidos: [{ repuesto_codigo: "FILT-05", cantidad: 3 }], creado_en_local: "2026-10-21T10:00:00Z",
});

describe("borradores y cierre atómico", () => {
  it("conserva solicitud y primera atención reales al cerrar", async () => {
    const b = { ...borrador(), fecha_solicitud: "2020-01-01T08:00:00.000Z", fecha_primera_atencion: "2020-01-01T10:00:00.000Z", repuestos_consumidos: [] };
    await db.borradoresOrden.add(b);
    await cerrarBorrador(b);
    expect(await db.ordenesLocal.get(b.id)).toMatchObject({ fecha_solicitud: b.fecha_solicitud, fecha_primera_atencion: b.fecha_primera_atencion });
  });
  it("rechaza fechas SLA incompletas o invertidas sin cerrar ni consumir", async () => {
    const b = { ...borrador(), fecha_solicitud: "2020-01-01T10:00:00.000Z", fecha_primera_atencion: "2020-01-01T08:00:00.000Z", repuestos_consumidos: [] };
    await db.borradoresOrden.add(b);
    await expect(cerrarBorrador(b)).rejects.toThrow(/atención/i);
    await expect(cerrarBorrador({ ...b, fecha_primera_atencion: "" })).rejects.toThrow(/ambas/i);
    expect(await db.ordenesLocal.count()).toBe(0);
  });
  it("una copia vieja no descarta la versión más reciente ni recrea un borrador descartado", async () => {
    const vieja = await abrirBorrador(2, "RO-1", 1);
    const reciente = await guardarBorrador({ ...vieja, lecturas: { ...vieja.lecturas, ph: "8" } });
    await expect(descartarBorrador(vieja)).rejects.toThrow(/otra pestaña/i);
    expect((await abrirBorrador(2, "RO-1", 1)).lecturas.ph).toBe("8");
    await descartarBorrador(reciente);
    await expect(guardarBorrador(reciente)).rejects.toThrow(/otra pestaña/i);
    expect(await db.borradoresOrden.count()).toBe(0);
  });
  it("rechaza que una pestaña sobrescriba cambios guardados desde otra", async () => {
    const a = await abrirBorrador(2, "RO-1", 1);
    const b = await abrirBorrador(2, "RO-1", 1);
    await guardarBorrador({ ...a, lecturas: { ...a.lecturas, ph: "8" } });
    await expect(guardarBorrador({ ...b, lecturas: { ...b.lecturas, tds_entrada_ppm: "350" } })).rejects.toThrow(/otra pestaña/i);
    expect((await abrirBorrador(2, "RO-1", 1)).lecturas.ph).toBe("8");
  });

  it("rechaza cerrar una copia vieja y conserva los cambios recientes", async () => {
    const base = await abrirBorrador(2, "RO-1", 1);
    const vieja = { ...borrador(), id: base.id, repuestos_consumidos: [] };
    await guardarBorrador(vieja);
    await expect(cerrarBorrador(vieja)).rejects.toThrow(/otra pestaña/i);
    expect(await db.ordenesLocal.count()).toBe(0);
    expect(await db.borradoresOrden.count()).toBe(1);
  });
  it("rechaza lecturas infinitas antes de serializarlas como null", async () => {
    const b = borrador(); b.lecturas.tds_entrada_ppm = "Infinity"; b.repuestos_consumidos = [];
    await db.borradoresOrden.add(b);
    await expect(cerrarBorrador(b)).rejects.toThrow(/lecturas/i);
    expect(await db.ordenesLocal.count()).toBe(0);
  });
  it("reabre el mismo borrador sin perder las lecturas o cambiar UUID", async () => {
    const b = borrador();
    await db.borradoresOrden.add(b);
    const recargado = await abrirBorrador(2, "RO-1", 1);
    expect(recargado).toEqual(b);
    const otro = await abrirBorrador(3, "RO-1", 1);
    expect(otro.id).not.toBe(b.id);
    expect(otro.lecturas.ph).toBe("");
  });

  it("guardar y descartar no consume stock", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno", 2);
    const b = borrador();
    await db.borradoresOrden.add(b);
    await descartarBorrador(b);
    expect((await db.stockPorTecnico.get([2, "FILT-05"]))?.cantidad_consumida).toBe(0);
    expect(await db.borradoresOrden.count()).toBe(0);
    expect(await db.ordenesLocal.count()).toBe(0);
  });

  it("cierra y reintenta el mismo UUID sin duplicar acta ni consumo", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno", 2);
    const b = borrador();
    await db.borradoresOrden.add(b);
    await Promise.all([cerrarBorrador(b), cerrarBorrador(b)]);
    expect(await db.ordenesLocal.count()).toBe(1);
    expect(await db.ordenesLocal.get(b.id)).toMatchObject({ estado_sync: "pendiente", tecnico_id: 2, lecturas_agua: { ph: 7 } });
    expect((await db.stockPorTecnico.get([2, "FILT-05"]))?.cantidad_consumida).toBe(3);
    expect(await db.borradoresOrden.count()).toBe(0);
  });

  it("si falla guardar el acta revierte consumos y conserva el borrador", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno", 2);
    const b = borrador();
    await db.borradoresOrden.add(b);
    vi.spyOn(db.ordenesLocal, "add").mockRejectedValueOnce(new Error("QuotaExceededError"));
    await expect(cerrarBorrador(b)).rejects.toThrow();
    expect((await db.stockPorTecnico.get([2, "FILT-05"]))?.cantidad_consumida).toBe(0);
    expect(await db.borradoresOrden.get([2, "RO-1"])).toEqual(b);
    expect(await db.ordenesLocal.count()).toBe(0);
  });

  it("revalida stock al cerrar y revierte todos los repuestos si alguno no alcanza", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno", 2);
    const b = borrador();
    b.repuestos_consumidos.push({ repuesto_codigo: "NO-CARGADO", cantidad: 1 });
    await db.borradoresOrden.add(b);
    await expect(cerrarBorrador(b)).rejects.toThrow(/stock/i);
    expect((await db.stockPorTecnico.get([2, "FILT-05"]))?.cantidad_consumida).toBe(0);
    expect(await db.borradoresOrden.count()).toBe(1);
  });

  it("bloquea el cierre de lecturas incompletas aunque se invoque fuera del formulario", async () => {
    const b = borrador(); b.lecturas.ph = "";
    await db.borradoresOrden.add(b);
    await expect(cerrarBorrador(b)).rejects.toThrow(/lecturas/i);
    expect(await db.ordenesLocal.count()).toBe(0);
  });

  it("un guardado rezagado no vuelve a crear un borrador ya cerrado", async () => {
    const b = borrador(); b.repuestos_consumidos = [];
    await db.borradoresOrden.add(b);
    await cerrarBorrador(b);
    await expect(guardarBorrador(b)).rejects.toThrow(/cerrad/i);
    expect(await db.borradoresOrden.count()).toBe(0);
  });
});
