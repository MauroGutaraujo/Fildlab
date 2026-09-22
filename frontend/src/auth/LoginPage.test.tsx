import { describe, expect, it, vi } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { LoginPage } from "./LoginPage";
import { renderWithProviders } from "../test/utils";

const app = (
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/" element={<div>inicio</div>} />
  </Routes>
);

async function llenar(email: string, pw: string) {
  await userEvent.type(screen.getByLabelText(/correo/i), email);
  await userEvent.type(screen.getByLabelText(/contraseña/i), pw);
  await userEvent.click(screen.getByRole("button", { name: /ingresar/i }));
}

describe("LoginPage", () => {
  it("éxito: llama a login y redirige al inicio", async () => {
    const { value } = renderWithProviders(app, { rol: null, route: "/login" });
    (value.login as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    await llenar("g@x.pe", "clave");
    expect(value.login).toHaveBeenCalledWith("g@x.pe", "clave");
    expect(await screen.findByText("inicio")).toBeInTheDocument();
  });

  it("credenciales malas muestran error y no redirigen", async () => {
    const { value } = renderWithProviders(app, { rol: null, route: "/login" });
    (value.login as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("Credenciales inválidas"));
    await llenar("g@x.pe", "mala");
    expect(await screen.findByRole("alert")).toHaveTextContent("Credenciales inválidas");
    expect(screen.queryByText("inicio")).not.toBeInTheDocument();
  });

  it("no envía con campos vacíos", async () => {
    const { value } = renderWithProviders(app, { rol: null, route: "/login" });
    await userEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    expect(value.login).not.toHaveBeenCalled();
  });

  it("deshabilita el botón mientras envía (evita doble envío)", async () => {
    const { value } = renderWithProviders(app, { rol: null, route: "/login" });
    let fin!: () => void;
    (value.login as ReturnType<typeof vi.fn>).mockReturnValue(new Promise<void>((r) => (fin = r)));
    await llenar("g@x.pe", "clave");
    await waitFor(() => expect(screen.getByRole("button", { name: /ingresando/i })).toBeDisabled());
    await act(async () => fin());
  });
});
