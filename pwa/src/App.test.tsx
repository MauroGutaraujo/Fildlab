import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "./App";
import { db } from "./db/dexie";

describe("App (PWA)", () => {
  it("sin sesion muestra el login de turno", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: /ingreso/i })).toBeInTheDocument();
  });

  it("con sesion guardada muestra el selector de equipo, no el login", async () => {
    await db.sesion.put({ id: "actual", token: "tok-ya-logueado", guardado_en: "2026-01-01" });
    render(<App />);
    expect(await screen.findByRole("heading", { name: /elegir equipo/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /ingreso/i })).not.toBeInTheDocument();
  });
});
