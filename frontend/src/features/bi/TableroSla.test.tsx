import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { TableroSla } from "./TableroSla";
import { mockApi, renderWithProviders } from "../../test/utils";

vi.mock("echarts-for-react/lib/core", () => ({
  default: (props: { option: unknown }) => <div data-testid="chart-sla">{JSON.stringify(props.option)}</div>,
}));

describe("TableroSla", () => {
  it("vacío muestra «Sin datos disponibles para el periodo»", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 0, ordenes_sin_medicion: 0, ordenes_fuera_sla: [], pct_cumplimiento: null } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText("Sin datos disponibles para el periodo")).toBeInTheDocument();
  });

  it("sin ninguna orden medida muestra el aviso, no un 100% falso", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 3, ordenes_sin_medicion: 3, ordenes_fuera_sla: [], pct_cumplimiento: null } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText(/tiene tiempo de respuesta medido todavía/i)).toBeInTheDocument();
    expect(screen.queryByTestId("chart-sla")).not.toBeInTheDocument();
  });

  it("100% de cumplimiento no muestra tabla de alertas, sí un mensaje positivo", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 5, ordenes_sin_medicion: 0, ordenes_fuera_sla: [], pct_cumplimiento: 100 } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText(/ninguna orden excedió el sla/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByTestId("chart-sla")).toHaveTextContent("#059669");
  });

  it("resume cumplimiento, respuesta promedio y desglose desde órdenes y contratos", async () => {
    mockApi([
      { path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 5, ordenes_sin_medicion: 1, ordenes_fuera_sla: [], pct_cumplimiento: 98 } },
      { path: "/api/v1/ordenes", body: [
        { id: "a", contrato_id: 1, fecha_creacion_cliente: "2026-09-10T12:00:00-05:00", tiempo_respuesta_horas: "2.00" },
        { id: "b", contrato_id: 1, fecha_creacion_cliente: "2026-09-11T12:00:00-05:00", tiempo_respuesta_horas: "2.80" },
        { id: "c", contrato_id: 1, fecha_creacion_cliente: "2026-08-31T23:00:00-05:00", tiempo_respuesta_horas: "7.00" },
      ] },
      { path: "/api/v1/contratos", body: [{ id: 1, sla_horas_max_respuesta: 4 }] },
    ]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText("SLA en Norma (Meta ≥ 98%)")).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/v1/ordenes", expect.anything());
    expect(screen.getByText("Tiempo Promedio de Respuesta")).toBeInTheDocument();
    expect(await screen.findByText(/2\.4 h/)).toHaveTextContent("de 4.0 h pactadas");
    expect(screen.getByText("Desglose de Servicios")).toBeInTheDocument();
    expect(screen.getByText("5").parentElement).toHaveTextContent("órdenes atendidas");
    expect(screen.getByText("4").parentElement).toHaveTextContent("servicios a tiempo");
  });

  it("marca riesgo cuando el SLA queda bajo 98%", async () => {
    mockApi([
      { path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 2, ordenes_sin_medicion: 0, ordenes_fuera_sla: [], pct_cumplimiento: 97 } },
      { path: "/api/v1/ordenes", body: [] },
      { path: "/api/v1/contratos", body: [] },
    ]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText("Riesgo de Penalización Contractual")).toBeInTheDocument();
    expect(screen.getByTestId("chart-sla")).toHaveTextContent("#d97706");
  });

  it("distingue una falla al cargar órdenes de un periodo sin tiempos medidos", async () => {
    mockApi([
      { path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 2, ordenes_sin_medicion: 0, ordenes_fuera_sla: [], pct_cumplimiento: 100 } },
      { path: "/api/v1/ordenes", status: 500, body: { detail: "Error cargando órdenes" } },
      { path: "/api/v1/contratos", body: [{ id: 1, sla_horas_max_respuesta: 4 }] },
    ]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText(/no se pudieron cargar los datos de órdenes para calcular el tiempo promedio/i)).toBeInTheDocument();
    expect(screen.queryByText(/sin tiempos medidos disponibles/i)).not.toBeInTheDocument();
  });

  it("omite comparar promedios cuando faltan SLA contractuales de algunas órdenes", async () => {
    mockApi([
      { path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 2, ordenes_sin_medicion: 0, ordenes_fuera_sla: [], pct_cumplimiento: 100 } },
      { path: "/api/v1/ordenes", body: [
        { id: "a", contrato_id: 1, fecha_creacion_cliente: "2026-09-10T12:00:00-05:00", tiempo_respuesta_horas: "2.00" },
        { id: "b", contrato_id: 99, fecha_creacion_cliente: "2026-09-11T12:00:00-05:00", tiempo_respuesta_horas: "3.00" },
      ] },
      { path: "/api/v1/contratos", body: [{ id: 1, sla_horas_max_respuesta: 4 }] },
    ]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText(/2\.5 h/)).toBeInTheDocument();
    expect(screen.getByText(/sla pactado no disponible para todos/i)).toBeInTheDocument();
    expect(screen.getByText(/comparación omitida: hay sla contractual disponible para 1 de 2/i)).toBeInTheDocument();
    expect(screen.queryByText(/de 4\.0 h pactadas/i)).not.toBeInTheDocument();
  });

  it("muestra el aviso de órdenes sin medición junto con el gráfico, cuando hay mediciones parciales", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", body: { periodo: "2026-09", total_ordenes: 4, ordenes_sin_medicion: 2, ordenes_fuera_sla: [], pct_cumplimiento: 100 } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByTestId("chart-sla")).toBeInTheDocument();
    expect(screen.getByText(/2 orden\(es\) sin tiempo de respuesta medido/i)).toBeInTheDocument();
  });

  it("muestra la tabla de órdenes fuera de SLA", async () => {
    mockApi([{
      path: "/api/v1/analytics/sla?periodo=2026-09",
      body: {
        periodo: "2026-09", total_ordenes: 2, ordenes_sin_medicion: 0, pct_cumplimiento: 50,
        ordenes_fuera_sla: [{
          orden_id: "11111111-1111-1111-1111-111111111111", equipo_serie: "RO-1",
          razon_social: "Clínica Test SAC", tiempo_respuesta_horas: "9.50", sla_horas_max_respuesta: 4,
        }],
      },
    }, { path: "/api/v1/clientes", body: [{ ruc: "20612493821", razon_social: "Clinica Test SAC" }] }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByText("RO-1")).toBeInTheDocument();
    expect(screen.getByText("Clínica Test SAC")).toBeInTheDocument();
    expect(screen.getByText("RUC: 20612493821")).toBeInTheDocument();
  });

  it("error muestra el mensaje de la API", async () => {
    mockApi([{ path: "/api/v1/analytics/sla?periodo=2026-09", status: 403, body: { detail: "Permisos insuficientes" } }]);
    renderWithProviders(<TableroSla periodo="2026-09" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Permisos insuficientes");
  });
});
