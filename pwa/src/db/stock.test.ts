import { describe, expect, it } from "vitest";
import { db } from "./dexie";
import { cargarStockTurno, consumir } from "./stock";

describe("stock movil local", () => {
  it("carga el stock de turno", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-1");
    const item = await db.stockMovilLocal.get("FILT-05");
    expect(item?.cantidad_cargada).toBe(10);
  });

  it("consumir dentro del limite incrementa cantidad_consumida", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-1");
    const r = await consumir("FILT-05", 3);
    expect(r.ok).toBe(true);
    expect((await db.stockMovilLocal.get("FILT-05"))?.cantidad_consumida).toBe(3);
  });

  it("cargar de nuevo a mitad de turno conserva el consumo ya registrado", async () => {
    // El tecnico se quedaba con 1, carga 5 mas: el consumo previo no debe borrarse.
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-1");
    await consumir("FILT-05", 9);
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 5 }], "turno-1");
    const item = await db.stockMovilLocal.get("FILT-05");
    expect(item?.cantidad_consumida).toBe(9);
    expect(item?.cantidad_cargada).toBe(15);
  });

  it("consumir mas de lo cargado se bloquea y no cambia el registro", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 2 }], "turno-1");
    const r = await consumir("FILT-05", 5);
    expect(r.ok).toBe(false);
    expect((await db.stockMovilLocal.get("FILT-05"))?.cantidad_consumida).toBe(0);
  });
});
