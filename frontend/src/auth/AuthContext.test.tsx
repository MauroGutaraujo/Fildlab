import { describe, expect, it } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./AuthContext";
import { getToken, setToken } from "./session";
import { mockApi } from "../test/utils";

function Probe() {
  const { user, loading, login, logout } = useAuth();
  if (loading) return <p>cargando</p>;
  return (
    <div>
      <p>{user ? `hola ${user.nombre} (${user.rol})` : "anónimo"}</p>
      <button onClick={() => login("g@x.pe", "pw").catch(() => {})}>entrar</button>
      <button onClick={logout}>salir</button>
    </div>
  );
}

const ME = { id: 1, nombre: "Elva", email: "g@x.pe", rol: "GERENCIA" };

describe("AuthProvider", () => {
  it("sin token queda anónimo sin llamar a la API", async () => {
    const f = mockApi([]);
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(await screen.findByText("anónimo")).toBeInTheDocument();
    expect(f).not.toHaveBeenCalled();
  });

  it("con token restaura la sesión desde /auth/me", async () => {
    setToken("abc");
    mockApi([{ path: "/api/v1/auth/me", body: ME }]);
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(await screen.findByText("hola Elva (GERENCIA)")).toBeInTheDocument();
  });

  it("token vencido: limpia y queda anónimo", async () => {
    setToken("viejo");
    mockApi([{ path: "/api/v1/auth/me", status: 401, body: { detail: "No autenticado" } }]);
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(await screen.findByText("anónimo")).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("login guarda el token y carga el usuario", async () => {
    mockApi([
      { method: "POST", path: "/api/v1/auth/login", body: { access_token: "nuevo", token_type: "bearer" } },
      { path: "/api/v1/auth/me", body: ME },
    ]);
    render(<AuthProvider><Probe /></AuthProvider>);
    await userEvent.click(await screen.findByText("entrar"));
    expect(await screen.findByText("hola Elva (GERENCIA)")).toBeInTheDocument();
    expect(getToken()).toBe("nuevo");
  });

  it("logout borra token y usuario", async () => {
    setToken("abc");
    mockApi([{ path: "/api/v1/auth/me", body: ME }]);
    render(<AuthProvider><Probe /></AuthProvider>);
    await userEvent.click(await screen.findByText("salir"));
    await waitFor(() => expect(screen.getByText("anónimo")).toBeInTheDocument());
    expect(getToken()).toBeNull();
  });

  it("un 401 en cualquier llamada posterior desloguea", async () => {
    setToken("abc");
    mockApi([{ path: "/api/v1/auth/me", body: ME }]);
    render(<AuthProvider><Probe /></AuthProvider>);
    await screen.findByText("hola Elva (GERENCIA)");
    act(() => {
      window.dispatchEvent(new Event("auth:unauthorized"));
    });
    expect(await screen.findByText("anónimo")).toBeInTheDocument();
  });
});
