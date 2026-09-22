import { ReactElement } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { AuthContext, type AuthValue, type Rol, type Usuario } from "../auth/AuthContext";

export const routerFuture = { v7_startTransition: true, v7_relativeSplatPath: true } as const;

export function usuario(rol: Rol): Usuario {
  return { id: 1, nombre: "Usuaria Test", email: "u@test.pe", rol };
}

export function renderWithProviders(ui: ReactElement, opts: { rol?: Rol | null; route?: string } = {}) {
  const { rol = "GERENCIA", route = "/" } = opts;
  const value: AuthValue = {
    user: rol ? usuario(rol) : null,
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
  };
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    value,
    ...render(
      <QueryClientProvider client={qc}>
        <AuthContext.Provider value={value}>
          <MemoryRouter initialEntries={[route]} future={routerFuture}>
            {ui}
          </MemoryRouter>
        </AuthContext.Provider>
      </QueryClientProvider>,
    ),
  };
}

type Ruta = { method?: string; path: string | RegExp; status?: number; body?: unknown };

/** Simula el backend en la frontera de red. Devuelve el mock para inspeccionar llamadas. */
export function mockApi(rutas: Ruta[]) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    const method = (init?.method ?? "GET").toUpperCase();
    const r = rutas.find(
      (x) => (x.method ?? "GET") === method && (typeof x.path === "string" ? x.path === url : x.path.test(url)),
    );
    if (!r) return new Response(JSON.stringify({ detail: `sin mock ${method} ${url}` }), { status: 599 });
    const status = r.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(r.body ?? {}), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
}
