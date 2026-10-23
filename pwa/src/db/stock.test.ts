import { describe, expect, it } from "vitest";
import { db } from "./dexie";
import { cargarStockTurno, consumir } from "./stock";

describe("stock movil local", () => {
  it("rechaza un saldo corrupto sin sobrescribirlo", async () => {
    await db.stockPorTecnico.put({ tecnico_id: 1, repuesto_codigo: "FILT-05", cantidad_cargada: NaN, cantidad_consumida: 0, turno_id: "t" });
    expect(await consumir("FILT-05", 1, 1)).toMatchObject({ ok: false });
    await expect(cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 5 }], "t", 1)).rejects.toThrow(/saldo/i);
    expect((await db.stockPorTecnico.get([1, "FILT-05"]))?.cantidad_cargada).toBeNaN();
  });
  it.each([NaN, Infinity, -1, 0, 1.5])("rechaza una carga inválida %s sin alterar el saldo", async (cantidad) => {
    await expect(cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad }], "turno-1", 1)).rejects.toThrow();
  });

  it("no permite consumir el stock de otro técnico", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 5 }], "turno-A", 1);
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 2 }], "turno-B", 2);
    expect(await consumir("FILT-05", 3, 2)).toMatchObject({ ok: false });
  });

  it.each([NaN, Infinity, -1, 0, 1.5])("rechaza un consumo inválido %s", async (cantidad) => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 5 }], "turno-A", 1);
    expect(await consumir("FILT-05", cantidad, 1)).toMatchObject({ ok: false });
  });

  it("carga el stock de turno", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-1", 1);
    const item = await db.stockPorTecnico.get([1, "FILT-05"]);
    expect(item?.cantidad_cargada).toBe(10);
  });

  it("consumir dentro del limite incrementa cantidad_consumida", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-1", 1);
    const r = await consumir("FILT-05", 3, 1);
    expect(r.ok).toBe(true);
    expect((await db.stockPorTecnico.get([1, "FILT-05"]))?.cantidad_consumida).toBe(3);
  });

  it("cargar de nuevo a mitad de turno conserva el consumo ya registrado", async () => {
    // El tecnico se quedaba con 1, carga 5 mas: el consumo previo no debe borrarse.
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-1", 1);
    await consumir("FILT-05", 9, 1);
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 5 }], "turno-1", 1);
    const item = await db.stockPorTecnico.get([1, "FILT-05"]);
    expect(item?.cantidad_consumida).toBe(9);
    expect(item?.cantidad_cargada).toBe(15);
  });

  it("consumir mas de lo cargado se bloquea y no cambia el registro", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 2 }], "turno-1", 1);
    const r = await consumir("FILT-05", 5, 1);
    expect(r.ok).toBe(false);
    expect((await db.stockPorTecnico.get([1, "FILT-05"]))?.cantidad_consumida).toBe(0);
  });
});
