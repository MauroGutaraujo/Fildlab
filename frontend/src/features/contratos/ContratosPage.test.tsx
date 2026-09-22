import { describe, expect, it, vi } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ContratosPage } from "./ContratosPage";
import { mockApi, renderWithProviders } from "../../test/utils";

const CONTRATO = {
  id: 1,
  cliente_ruc: "20612493821",
  fecha_inicio: "2026-01-01",
  fecha_fin: "2026-12-31",
  monto_mensual_soles: "1500.00",
  sla_horas_max_respuesta: 6,
  estado: "ACTIVO",
};

async function llenar(o: { ruc?: string; inicio?: string; fin?: string; monto?: string; sla?: string } = {}) {
  await userEvent.type(screen.getByLabelText(/RUC del cliente/i), o.ruc ?? "20612493821");
  fireEvent.change(screen.getByLabelText(/inicio/i), { target: { value: o.inicio ?? "2026-01-01" } });
  fireEvent.change(screen.getByLabelText(/fin/i), { target: { value: o.fin ?? "2026-12-31" } });
  await userEvent.type(screen.getByLabelText(/monto/i), o.monto ?? "1500");
  const sla = screen.getByLabelText(/sla/i);
  await userEvent.clear(sla);
  await userEvent.type(sla, o.sla ?? "6");
}

const llamadas = (f: ReturnType<typeof mockApi>, metodo: string) =>
  f.mock.calls.filter(([, init]) => ((init as RequestInit | undefined)?.method ?? "GET") === metodo);

describe("ContratosPage", () => {
  it("TECNICO ve contratos sin acciones de escritura (RN-01)", async () => {
    mockApi([{ path: "/api/v1/contratos", body: [CONTRATO] }]);
    renderWithProviders(<ContratosPage />, { rol: "TECNICO" });
    expect(await screen.findByText("20612493821")).toBeInTheDocument();
    for (const n of [/nuevo contrato/i, /editar/i, /anular/i]) {
      expect(screen.queryByRole("button", { name: n })).not.toBeInTheDocument();
    }
  });

  it("muestra vigencia, monto y SLA", async () => {
    mockApi([{ path: "/api/v1/contratos", body: [CONTRATO] }]);
    renderWithProviders(<ContratosPage />);
    expect(await screen.findByText("2026-01-01 → 2026-12-31")).toBeInTheDocument();
    expect(screen.getByText("S/ 1500.00")).toBeInTheDocument();
    expect(screen.getByText("6 h")).toBeInTheDocument();
  });

  it("fecha fin anterior al inicio se rechaza antes de enviar", async () => {
    const f = mockApi([{ path: "/api/v1/contratos", body: [] }]);
    renderWithProviders(<ContratosPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo contrato/i }));
    await llenar({ inicio: "2026-06-01", fin: "2026-01-01" });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/no puede ser anterior/i)).toBeInTheDocument();
    expect(llamadas(f, "POST")).toHaveLength(0);
  });

  it.each(["0", "-5", "abc"])("monto «%s» se rechaza", async (monto) => {
    const f = mockApi([{ path: "/api/v1/contratos", body: [] }]);
    renderWithProviders(<ContratosPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo contrato/i }));
    await llenar({ monto });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/monto debe ser mayor que 0/i)).toBeInTheDocument();
    expect(llamadas(f, "POST")).toHaveLength(0);
  });

  it.each(["0", "-1", "1.5"])("SLA «%s» se rechaza", async (sla) => {
    const f = mockApi([{ path: "/api/v1/contratos", body: [] }]);
    renderWithProviders(<ContratosPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo contrato/i }));
    await llenar({ sla });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/sla debe ser un entero/i)).toBeInTheDocument();
    expect(llamadas(f, "POST")).toHaveLength(0);
  });

  it("RUC de 10 dígitos se rechaza", async () => {
    const f = mockApi([{ path: "/api/v1/contratos", body: [] }]);
    renderWithProviders(<ContratosPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo contrato/i }));
    await llenar({ ruc: "2061249382" });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/exactamente 11 dígitos/i)).toBeInTheDocument();
    expect(llamadas(f, "POST")).toHaveLength(0);
  });

  it("datos válidos envían el POST con los tipos que espera la API", async () => {
    const f = mockApi([
      { path: "/api/v1/contratos", body: [] },
      { method: "POST", path: "/api/v1/contratos", status: 201, body: CONTRATO },
    ]);
    renderWithProviders(<ContratosPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo contrato/i }));
    await llenar();
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nuevo contrato/i });
    const [, init] = llamadas(f, "POST")[0];
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      cliente_ruc: "20612493821",
      fecha_inicio: "2026-01-01",
      fecha_fin: "2026-12-31",
      monto_mensual_soles: "1500",
      sla_horas_max_respuesta: 6,
    });
  });

  it("muestra el error del backend (cliente inexistente)", async () => {
    mockApi([
      { path: "/api/v1/contratos", body: [] },
      { method: "POST", path: "/api/v1/contratos", status: 404, body: { detail: "Cliente no encontrado" } },
    ]);
    renderWithProviders(<ContratosPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo contrato/i }));
    await llenar();
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Cliente no encontrado");
  });

  it("anular pide confirmación y llama al endpoint", async () => {
    const f = mockApi([
      { path: "/api/v1/contratos", body: [CONTRATO] },
      { method: "POST", path: "/api/v1/contratos/1/anular", body: { ...CONTRATO, estado: "ANULADO" } },
    ]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithProviders(<ContratosPage />);
    await userEvent.click(await screen.findByRole("button", { name: /anular/i }));
    await vi.waitFor(() => expect(llamadas(f, "POST")).toHaveLength(1));
  });

  it("si el usuario cancela la confirmación no se anula", async () => {
    const f = mockApi([{ path: "/api/v1/contratos", body: [CONTRATO] }]);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    renderWithProviders(<ContratosPage />);
    await userEvent.click(await screen.findByRole("button", { name: /anular/i }));
    expect(llamadas(f, "POST")).toHaveLength(0);
  });

  it("un contrato ANULADO no ofrece editar ni anular", async () => {
    mockApi([{ path: "/api/v1/contratos", body: [{ ...CONTRATO, estado: "ANULADO" }] }]);
    renderWithProviders(<ContratosPage />);
    await screen.findByText("ANULADO");
    expect(screen.queryByRole("button", { name: /anular/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/contratos", body: [] }]);
    renderWithProviders(<ContratosPage />);
    expect(await screen.findByText("Sin datos disponibles")).toBeInTheDocument();
  });
});
