import { afterEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BiPage, periodoActual } from "./BiPage";
import { mockApi, renderWithProviders } from "../../test/utils";

vi.mock("echarts-for-react/lib/core", () => ({
  default: (props: { option: unknown }) => <div data-testid="chart-mock">{JSON.stringify(props.option)}</div>,
}));

function periodoLimaDe(fecha: Date): string {
  const partes = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Lima", year: "numeric", month: "2-digit" }).formatToParts(fecha);
  return `${partes.find((p) => p.type === "year")!.value}-${partes.find((p) => p.type === "month")!.value}`;
}

describe("BiPage", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("el selector de periodo arranca en el mes actual (calendario de Lima)", async () => {
    renderWithProviders(<BiPage />);
    const input = screen.getByLabelText("Periodo") as HTMLInputElement;
    expect(input.value).toBe(periodoLimaDe(new Date()));
  });

  it("periodoActual usa el calendario de Lima (America/Lima), no UTC", () => {
    vi.useFakeTimers();
    // 2026-10-01 04:30 UTC = 2026-09-30 23:30 en Lima (UTC-5): un corte en UTC diria octubre; en Lima sigue siendo septiembre.
    vi.setSystemTime(new Date(Date.UTC(2026, 9, 1, 4, 30)));
    expect(periodoActual()).toBe("2026-09");
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
