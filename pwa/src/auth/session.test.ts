import { describe, expect, it } from "vitest";
import { guardarSesionTurno, obtenerToken, cerrarSesion } from "./session";

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
});
