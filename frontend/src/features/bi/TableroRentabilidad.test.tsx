import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { TableroRentabilidad } from "./TableroRentabilidad";
import { mockApi, renderWithProviders } from "../../test/utils";

vi.mock("echarts-for-react/lib/core", () => ({
  default: (props: { option: unknown }) => <div data-testid="chart-rentabilidad">{JSON.stringify(props.option)}</div>,
}));

const RESP = {
  periodo: "2026-09",
  contratos: [
    {
      contrato_id: 1,
      cliente_ruc: "20612493821",
      razon_social: "Clínica Test SAC",
      ingreso_soles: "2500.00",
      costo_repuestos_soles: "10.00",
      margen_soles: "2490.00",
      margen_pct: 99.6,
    },
  ],
};

describe("TableroRentabilidad", () => {
  it("muestra el spinner mientras carga", () => {
    mockApi([{ path: "/api/v1/analytics/rentabilidad?periodo=2026-09", body: RESP }]);
    renderWithProviders(<TableroRentabilidad periodo="2026-09" />);
    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
  });

  it("renderiza el gráfico con los datos del contrato", async () => {
    mockApi([{ path: "/api/v1/analytics/rentabilidad?periodo=2026-09", body: RESP }]);
    renderWithProviders(<TableroRentabilidad periodo="2026-09" />);
    const chart = await screen.findByTestId("chart-rentabilidad");
    expect(chart.textContent).toContain("Clínica Test SAC");
    expect(chart.textContent).toContain("99.6");
  });

  it("vacío muestra «Sin datos disponibles para el periodo»", async () => {
    mockApi([{ path: "/api/v1/analytics/rentabilidad?periodo=2026-09", body: { periodo: "2026-09", contratos: [] } }]);
    renderWithProviders(<TableroRentabilidad periodo="2026-09" />);
    expect(await screen.findByText("Sin datos disponibles para el periodo")).toBeInTheDocument();
  });

  it("error muestra el mensaje de la API", async () => {
    mockApi([{ path: "/api/v1/analytics/rentabilidad?periodo=2026-09", status: 403, body: { detail: "Permisos insuficientes" } }]);
    renderWithProviders(<TableroRentabilidad periodo="2026-09" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Permisos insuficientes");
  });
});
