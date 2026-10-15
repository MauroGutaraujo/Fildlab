import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VentasPage } from "./VentasPage";
import { mockApi, renderWithProviders } from "../../test/utils";

const VENTA = {
  id: 1,
  cliente_ruc: "20612493821",
  usuario_id: 1,
  total_soles: "60.00",
  fecha: "2026-03-01T10:00:00Z",
  items: [{ repuesto_codigo: "FILT-05", cantidad: 3, precio_unitario_soles: "20.00" }],
};
const posts = (f: ReturnType<typeof mockApi>) =>
  f.mock.calls.filter(([, i]) => (i as RequestInit | undefined)?.method === "POST");

async function abrir() {
  await userEvent.click(await screen.findByRole("button", { name: /nueva venta/i }));
}
async function item(n: number, codigo: string, cant: string, precio: string) {
  await userEvent.type(screen.getByLabelText(`Código de repuesto ${n}`), codigo);
  await userEvent.type(screen.getByLabelText(`Cantidad ${n}`), cant);
  await userEvent.type(screen.getByLabelText(`Precio unitario (S/) ${n}`), precio);
}

describe("VentasPage", () => {
  it("lista las ventas con su total", async () => {
    mockApi([
      { path: "/api/v1/ventas", body: [VENTA] },
      { path: "/api/v1/clientes", body: [{ ruc: VENTA.cliente_ruc, razon_social: "Clínica Demo S.A." }] },
    ]);
    renderWithProviders(<VentasPage />);
    expect(await screen.findByText("S/ 60.00")).toBeInTheDocument();
    expect(screen.getByText("Clínica Demo S.A.")).toBeInTheDocument();
    expect(screen.getByText("RUC: 20612493821")).toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/ventas", body: [] }]);
    renderWithProviders(<VentasPage />);
    expect(await screen.findByText("Sin datos disponibles")).toBeInTheDocument();
  });

  it("TECNICO no puede crear ventas", async () => {
    mockApi([{ path: "/api/v1/ventas", body: [VENTA] }]);
    renderWithProviders(<VentasPage />, { rol: "TECNICO" });
    await screen.findByText("S/ 60.00");
    expect(screen.queryByRole("button", { name: /nueva venta/i })).not.toBeInTheDocument();
  });

  it("calcula el total en vivo y agrega/quita ítems", async () => {
    mockApi([{ path: "/api/v1/ventas", body: [] }]);
    renderWithProviders(<VentasPage />);
    await abrir();
    await item(1, "FILT-05", "3", "20");
    await userEvent.click(screen.getByRole("button", { name: /agregar ítem/i }));
    await item(2, "MEMB-01", "1", "99.90");
    expect(screen.getByText("Total: S/ 159.90")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Quitar ítem 2" }));
    expect(screen.getByText("Total: S/ 60.00")).toBeInTheDocument();
    expect(screen.queryByLabelText("Cantidad 2")).not.toBeInTheDocument();
  });

  it("no permite quitar el único ítem", async () => {
    mockApi([{ path: "/api/v1/ventas", body: [] }]);
    renderWithProviders(<VentasPage />);
    await abrir();
    expect(screen.queryByRole("button", { name: "Quitar ítem 1" })).not.toBeInTheDocument();
  });

  it("envía la venta con el body que espera la API", async () => {
    const f = mockApi([
      { path: "/api/v1/ventas", body: [] },
      { method: "POST", path: "/api/v1/ventas", status: 201, body: VENTA },
    ]);
    renderWithProviders(<VentasPage />);
    await abrir();
    await userEvent.type(screen.getByLabelText(/RUC del cliente/i), "20612493821");
    await item(1, "FILT-05", "3", "20.00");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nueva venta/i });
    expect(JSON.parse((posts(f)[0][1] as RequestInit).body as string)).toEqual({
      cliente_ruc: "20612493821",
      items: [{ repuesto_codigo: "FILT-05", cantidad: 3, precio_unitario_soles: "20.00" }],
    });
  });

  it("rechaza RUC inválido, cantidad 0, precio negativo y código vacío", async () => {
    const f = mockApi([{ path: "/api/v1/ventas", body: [] }]);
    renderWithProviders(<VentasPage />);
    await abrir();
    await userEvent.type(screen.getByLabelText(/RUC del cliente/i), "123");
    await item(1, " ", "0", "-5");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/exactamente 11 dígitos/i)).toBeInTheDocument();
    expect(screen.getByText(/código es obligatorio/i)).toBeInTheDocument();
    expect(screen.getByText(/cantidad debe ser un entero/i)).toBeInTheDocument();
    expect(screen.getByText(/precio debe ser/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("muestra el 409 de stock insuficiente sin cerrar el formulario", async () => {
    mockApi([
      { path: "/api/v1/ventas", body: [] },
      { method: "POST", path: "/api/v1/ventas", status: 409, body: { detail: "MEMB-01: stock 2, se piden 5" } },
    ]);
    renderWithProviders(<VentasPage />);
    await abrir();
    await userEvent.type(screen.getByLabelText(/RUC del cliente/i), "20612493821");
    await item(1, "MEMB-01", "5", "10");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("stock 2, se piden 5");
    expect(screen.getByLabelText("Cantidad 1")).toBeInTheDocument();
  });
});
