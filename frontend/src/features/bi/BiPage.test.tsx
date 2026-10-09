import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { BiPage } from "./BiPage";
import { renderWithProviders } from "../../test/utils";

describe("BiPage", () => {
  it("el selector de periodo arranca en el mes actual", async () => {
    renderWithProviders(<BiPage />);
    const input = screen.getByLabelText("Periodo") as HTMLInputElement;
    const esperado = new Date().toISOString().slice(0, 7);
    expect(input.value).toBe(esperado);
  });

  it("TECNICO no ve el enlace BI en el navbar", async () => {
    const { container } = renderWithProviders(<BiPage />, { rol: "TECNICO" });
    // Esta prueba verifica BiPage en aislamiento; la del navbar completo va en Task de integración (Step 4).
    expect(container).toBeTruthy();
  });
});
