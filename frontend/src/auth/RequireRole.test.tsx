import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { RequireRole } from "./RequireRole";
import { renderWithProviders, routerFuture } from "../test/utils";

const app = (
  <Routes>
    <Route path="/login" element={<div>pantalla login</div>} />
    <Route
      path="/clientes"
      element={
        <RequireRole roles={["GERENCIA"]}>
          <div>contenido de gerencia</div>
        </RequireRole>
      }
    />
  </Routes>
);

describe("RequireRole", () => {
  it("sin sesión redirige a /login", () => {
    renderWithProviders(app, { rol: null, route: "/clientes" });
    expect(screen.getByText("pantalla login")).toBeInTheDocument();
  });

  it("TECNICO en ruta de Gerencia ve «Acceso denegado»", () => {
    renderWithProviders(app, { rol: "TECNICO", route: "/clientes" });
    expect(screen.getByText(/acceso denegado/i)).toBeInTheDocument();
    expect(screen.queryByText("contenido de gerencia")).not.toBeInTheDocument();
  });

  it("GERENCIA accede", () => {
    renderWithProviders(app, { rol: "GERENCIA", route: "/clientes" });
    expect(screen.getByText("contenido de gerencia")).toBeInTheDocument();
  });

  it("mientras carga la sesión no redirige ni muestra contenido", async () => {
    const { AuthContext } = await import("./AuthContext");
    const { render } = await import("@testing-library/react");
    const { MemoryRouter } = await import("react-router-dom");
    render(
      <AuthContext.Provider value={{ user: null, loading: true, login: async () => {}, logout: () => {} }}>
        <MemoryRouter initialEntries={["/clientes"]} future={routerFuture}>
          {app}
        </MemoryRouter>
      </AuthContext.Provider>,
    );
    expect(screen.queryByText("pantalla login")).not.toBeInTheDocument();
    expect(screen.queryByText("contenido de gerencia")).not.toBeInTheDocument();
  });
});
