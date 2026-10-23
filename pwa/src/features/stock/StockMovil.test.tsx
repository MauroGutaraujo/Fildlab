import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StockMovil } from "./StockMovil";
import { db } from "../../db/dexie";

describe("StockMovil", () => {
  it("registra la carga de turno y la refleja en Dexie", async () => {
    render(<StockMovil tecnicoId={2} />);
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/cantidad cargada/i), "10");
    await userEvent.click(screen.getByRole("button", { name: /cargar/i }));
    await waitFor(async () => expect((await db.stockPorTecnico.get([2, "FILT-05"]))?.cantidad_cargada).toBe(10));
  });

  it.each(["abc", "-2", "1.5", "Infinity"])("rechaza la carga %s y muestra el error", async (cantidad) => {
    render(<StockMovil tecnicoId={2} />);
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/cantidad cargada/i), cantidad);
    await userEvent.click(screen.getByRole("button", { name: /cargar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/entera positiva/i);
    expect(await db.stockPorTecnico.count()).toBe(0);
  });

  it("advierte sobre stock antiguo sin atribuirlo al usuario actual", async () => {
    await db.stockMovilLocal.put({ repuesto_codigo: "FILT-05", cantidad_cargada: 10, cantidad_consumida: 3, turno_id: "viejo" });
    render(<StockMovil tecnicoId={2} />);
    expect(await screen.findByText(/stock anterior sin técnico asignado/i)).toBeInTheDocument();
    expect(await db.stockPorTecnico.count()).toBe(0);
    expect((await db.stockMovilLocal.get("FILT-05"))?.cantidad_cargada).toBe(10);
  });
});
