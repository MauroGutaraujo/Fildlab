import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StockMovil } from "./StockMovil";
import { db } from "../../db/dexie";

describe("StockMovil", () => {
  it("registra la carga de turno y la refleja en Dexie", async () => {
    render(<StockMovil />);
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/cantidad cargada/i), "10");
    await userEvent.click(screen.getByRole("button", { name: /cargar/i }));
    await waitFor(async () => expect((await db.stockMovilLocal.get("FILT-05"))?.cantidad_cargada).toBe(10));
  });
});
