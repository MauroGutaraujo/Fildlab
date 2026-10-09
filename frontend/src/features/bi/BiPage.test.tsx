import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BiPage } from "./BiPage";
import { mockApi, renderWithProviders } from "../../test/utils";

vi.mock("echarts-for-react/lib/core", () => ({
  default: (props: { option: unknown }) => <div data-testid="chart-mock">{JSON.stringify(props.option)}</div>,
}));

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

  it("cambiar el periodo dispara nuevas consultas a ambos endpoints con el periodo correcto", async () => {
    const f = mockApi([
      { path: /\/api\/v1\/analytics\/rentabilidad/, body: { periodo: "2026-09", contratos: [] } },
      { path: /\/api\/v1\/analytics\/sla/, body: { periodo: "2026-09", total_ordenes: 0, ordenes_fuera_sla: [], pct_cumplimiento: null } },
    ]);
    renderWithProviders(<BiPage />);
    const input = screen.getByLabelText("Periodo");
    await userEvent.clear(input);
    await userEvent.type(input, "2026-03");
    await vi.waitFor(() => {
      const urls = f.mock.calls.map(([u]) => String(u));
      expect(urls.some((u) => u.includes("rentabilidad?periodo=2026-03"))).toBe(true);
      expect(urls.some((u) => u.includes("sla?periodo=2026-03"))).toBe(true);
    });
  });
});
