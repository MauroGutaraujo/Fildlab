import { describe, expect, it } from "vitest";
import { guardarSesionTurno, obtenerToken, cerrarSesion, decodeTecnicoId } from "./session";
import { tokenDeTecnico } from "../test/token";

describe("sesion de turno", () => {
  it("guarda el token en IndexedDB, no en sessionStorage", async () => {
    await guardarSesionTurno("tok-123");
    expect(sessionStorage.getItem("fildlab.token")).toBeNull();
    expect(await obtenerToken()).toBe("tok-123");
  });

  it("cerrarSesion borra el token guardado", async () => {
    await guardarSesionTurno("tok-456");
    await cerrarSesion();
    expect(await obtenerToken()).toBeNull();
  });

  it.each(["tok-invalido", `x.${btoa('{"sub":"1"}')}.x`, tokenDeTecnico(-1), tokenDeTecnico(1.5), tokenDeTecnico(NaN)])("no deriva un técnico de un JWT inválido: %s", (token) => {
    expect(decodeTecnicoId(token)).toBeNull();
  });

  it("conserva identidad válida de un token vencido para trabajar offline", () => {
    expect(decodeTecnicoId(tokenDeTecnico(7, 1))).toBe(7);
  });

  it("rechaza una firma que ni siquiera es base64url decodificable", () => {
    const partes = tokenDeTecnico().split(".");
    expect(decodeTecnicoId(`${partes[0]}.${partes[1]}.a`)).toBeNull();
  });
});
