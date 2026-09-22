import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { AppRoutes } from "./App";
import { mockApi, renderWithProviders } from "./test/utils";

const vacias = [
  { path: "/api/v1/clientes", body: [] },
  { path: "/api/v1/contratos", body: [] },
  { path: "/api/v1/equipos", body: [] },
  { path: "/api/v1/repuestos", body: [] },
  { path: "/api/v1/inventario/movimientos", body: [] },
  { path: "/api/v1/ventas", body: [] },
  { path: /\/api\/v1\/ordenes/, body: [] },
];

describe("AppRoutes", () => {
  it("sin sesión cualquier ruta protegida redirige al login", () => {
    mockApi(vacias);
    renderWithProviders(<AppRoutes />, { rol: null, route: "/clientes" });
    expect(screen.getByRole("heading", { name: /ingreso/i })).toBeInTheDocument();
  });

  it("la raíz lleva a Clientes", async () => {
    mockApi(vacias);
    renderWithProviders(<AppRoutes />, { rol: "GERENCIA", route: "/" });
    expect(await screen.findByRole("heading", { name: "Clientes" })).toBeInTheDocument();
  });

  it("GERENCIA ve todo el menú", () => {
    mockApi(vacias);
    renderWithProviders(<AppRoutes />, { rol: "GERENCIA", route: "/clientes" });
    const nav = screen.getByRole("navigation");
    for (const t of ["Clientes", "Contratos", "Equipos", "Inventario", "Ventas", "Liquidación"]) {
      expect(nav).toHaveTextContent(t);
    }
  });

  it("TECNICO no ve Ventas ni Liquidación en el menú", () => {
    mockApi(vacias);
    renderWithProviders(<AppRoutes />, { rol: "TECNICO", route: "/clientes" });
    const nav = screen.getByRole("navigation");
    expect(nav).toHaveTextContent("Clientes");
    expect(nav).not.toHaveTextContent("Ventas");
    expect(nav).not.toHaveTextContent("Liquidación");
  });

  it.each(["/liquidacion", "/ventas"])("TECNICO en %s ve «Acceso denegado»", (ruta) => {
    mockApi(vacias);
    renderWithProviders(<AppRoutes />, { rol: "TECNICO", route: ruta });
    expect(screen.getByText(/acceso denegado/i)).toBeInTheDocument();
  });

  it("GERENCIA accede a Liquidación", async () => {
    mockApi(vacias);
    renderWithProviders(<AppRoutes />, { rol: "GERENCIA", route: "/liquidacion" });
    expect(await screen.findByRole("heading", { name: /liquidación/i, level: 1 })).toBeInTheDocument();
  });

  it("ruta desconocida muestra «Página no encontrada»", () => {
    mockApi(vacias);
    renderWithProviders(<AppRoutes />, { rol: "GERENCIA", route: "/nada" });
    expect(screen.getByText(/página no encontrada/i)).toBeInTheDocument();
  });

  it("el botón Salir cierra la sesión", async () => {
    mockApi(vacias);
    const { value } = renderWithProviders(<AppRoutes />, { rol: "GERENCIA", route: "/clientes" });
    screen.getByRole("button", { name: /salir/i }).click();
    expect(value.logout).toHaveBeenCalled();
  });
});
