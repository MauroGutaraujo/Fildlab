import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginTurno } from "./LoginTurno";
import { obtenerToken } from "./session";

describe("LoginTurno", () => {
  it("envia duracion=turno y guarda el token recibido", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ access_token: "tok-789", token_type: "bearer" }), { status: 200 }),
    );
    render(<LoginTurno onIngreso={() => {}} />);
    await userEvent.type(screen.getByLabelText(/correo/i), "t@x.pe");
    await userEvent.type(screen.getByLabelText(/contraseña/i), "clave");
    await userEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    await waitFor(async () => expect(await obtenerToken()).toBe("tok-789"));
    const body = JSON.parse((f.mock.calls[0][1] as RequestInit).body as string);
    expect(body.duracion).toBe("turno");
  });

  it("credenciales invalidas muestran error y no guardan token", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Credenciales inválidas" }), { status: 401 }),
    );
    render(<LoginTurno onIngreso={() => {}} />);
    await userEvent.type(screen.getByLabelText(/correo/i), "t@x.pe");
    await userEvent.type(screen.getByLabelText(/contraseña/i), "mala");
    await userEvent.click(screen.getByRole("button", { name: /ingresar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Credenciales inválidas");
    await waitFor(async () => expect(await obtenerToken()).toBeNull());
  });
});
