import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClientesPage } from "./ClientesPage";
import { mockApi, renderWithProviders } from "../../test/utils";

const CLIENTE = { ruc: "20612493821", razon_social: "Clínica Norte SAC", direccion: "Av. España 100", activo: true };

async function llenarForm(ruc: string) {
  await userEvent.type(screen.getByLabelText("RUC"), ruc);
  await userEvent.type(screen.getByLabelText("Razón social"), "Nueva SAC");
  await userEvent.type(screen.getByLabelText("Dirección"), "Calle 1");
}

const llamadas = (f: ReturnType<typeof mockApi>, metodo: string) =>
  f.mock.calls.filter(([, init]) => ((init as RequestInit | undefined)?.method ?? "GET") === metodo);

describe("ClientesPage", () => {
  it("TECNICO ve la lista en solo lectura (RN-01)", async () => {
    mockApi([{ path: "/api/v1/clientes", body: [CLIENTE] }]);
    renderWithProviders(<ClientesPage />, { rol: "TECNICO" });
    expect(await screen.findByText("Clínica Norte SAC")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /nuevo cliente/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
  });

  it("GERENCIA ve los botones de crear y editar", async () => {
    mockApi([{ path: "/api/v1/clientes", body: [CLIENTE] }]);
    renderWithProviders(<ClientesPage />, { rol: "GERENCIA" });
    expect(await screen.findByRole("button", { name: /editar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /nuevo cliente/i })).toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/clientes", body: [] }]);
    renderWithProviders(<ClientesPage />);
    expect(await screen.findByText("Sin datos disponibles")).toBeInTheDocument();
  });

  it.each(["123", "1234567890", "2061249382a", "20612 93821"])("RUC inválido «%s» se rechaza antes de enviar", async (ruc) => {
    const f = mockApi([{ path: "/api/v1/clientes", body: [] }]);
    renderWithProviders(<ClientesPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo cliente/i }));
    await llenarForm(ruc);
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/exactamente 11 dígitos/i)).toBeInTheDocument();
    expect(llamadas(f, "POST")).toHaveLength(0);
  });

  it("RUC válido envía el POST y cierra el formulario", async () => {
    const f = mockApi([
      { path: "/api/v1/clientes", body: [] },
      { method: "POST", path: "/api/v1/clientes", status: 201, body: CLIENTE },
    ]);
    renderWithProviders(<ClientesPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo cliente/i }));
    await llenarForm("20612493821");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nuevo cliente/i });
    const [, init] = llamadas(f, "POST")[0];
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      ruc: "20612493821",
      razon_social: "Nueva SAC",
      direccion: "Calle 1",
    });
    expect(screen.queryByLabelText("RUC")).not.toBeInTheDocument();
  });

  it("muestra el 409 del backend (RUC duplicado) sin cerrar el formulario", async () => {
    mockApi([
      { path: "/api/v1/clientes", body: [CLIENTE] },
      { method: "POST", path: "/api/v1/clientes", status: 409, body: { detail: "Ya existe un cliente con ese RUC" } },
    ]);
    renderWithProviders(<ClientesPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo cliente/i }));
    await llenarForm("20612493821");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe un cliente con ese RUC");
    expect(screen.getByLabelText("RUC")).toBeInTheDocument();
  });

  it("no permite enviar razón social ni dirección en blanco", async () => {
    const f = mockApi([{ path: "/api/v1/clientes", body: [] }]);
    renderWithProviders(<ClientesPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo cliente/i }));
    await userEvent.type(screen.getByLabelText("RUC"), "20612493821");
    await userEvent.type(screen.getByLabelText("Razón social"), "   ");
    await userEvent.type(screen.getByLabelText("Dirección"), "   ");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/razón social es obligatoria/i)).toBeInTheDocument();
    expect(llamadas(f, "POST")).toHaveLength(0);
  });

  it("editar: el RUC queda bloqueado y se envía PUT", async () => {
    const f = mockApi([
      { path: "/api/v1/clientes", body: [CLIENTE] },
      { method: "PUT", path: "/api/v1/clientes/20612493821", body: { ...CLIENTE, razon_social: "Otra SAC" } },
    ]);
    renderWithProviders(<ClientesPage />);
    await userEvent.click(await screen.findByRole("button", { name: /editar/i }));
    expect(screen.getByLabelText("RUC")).toBeDisabled();
    const razon = screen.getByLabelText("Razón social");
    await userEvent.clear(razon);
    await userEvent.type(razon, "Otra SAC");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nuevo cliente/i });
    const [, init] = llamadas(f, "PUT")[0];
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({ razon_social: "Otra SAC", direccion: "Av. España 100" });
  });

  it("muestra cuáles clientes están anulados", async () => {
    mockApi([{ path: "/api/v1/clientes", body: [{ ...CLIENTE, activo: false }] }]);
    renderWithProviders(<ClientesPage />);
    const fila = (await screen.findByText("Clínica Norte SAC")).closest("tr")!;
    expect(within(fila).getByText("Anulado")).toBeInTheDocument();
  });

  it("si la carga falla muestra el error", async () => {
    mockApi([{ path: "/api/v1/clientes", status: 500, body: { detail: "Error interno" } }]);
    renderWithProviders(<ClientesPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Error interno");
  });
});
