import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { TableroSla } from "./TableroSla";
import { mockApi, renderWithProviders } from "../../test/utils";

vi.mock("echarts-for-react/lib/core", () => ({
  default: (props: { option: unknown }) => <div data-testid="chart-sla">{JSON.stringify(props.option)}</div>,
}));

describe("TableroSla", () => {
  it("vacío muestra «Sin datos disponibles para el periodo»", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 0, ordenes_fuera_sla: [], pct_cumplimiento: null } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText("Sin datos disponibles para el periodo")).toBeInTheDocument();
  });

  it("100% de cumplimiento no muestra tabla de alertas, sí un mensaje positivo", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 5, ordenes_fuera_sla: [], pct_cumplimiento: 100 } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText(/ninguna orden excedió el sla/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("muestra la tabla de órdenes fuera de SLA", async () => {
    mockApi([{
      path: "/api/v1/analytics/sla?periodo=2026-09",
      body: {
        periodo: "2026-09", total_ordenes: 2, pct_cumplimiento: 50,
        ordenes_fuera_sla: [{
          orden_id: "11111111-1111-1111-1111-111111111111", equipo_serie: "RO-1",
          razon_social: "Clínica Test SAC", tiempo_respuesta_horas: "9.50", sla_horas_max_respuesta: 4,
        }],
      },
    }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText("RO-1")).toBeInTheDocument();
    expect(screen.getByText("Clínica Test SAC")).toBeInTheDocument();
  });

  it("error muestra el mensaje de la API", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", status: 403, body: { detail: "Permisos insuficientes" } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Permisos insuficientes");
  });
});
