import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  it("«Sincronizar ahora» usa TanStack Query (useMutation) para procesar el Outbox", async () => {
    await db.sesion.put({ id: "actual", token: "tok-ya-logueado", guardado_en: "2026-01-01" });
    await db.ordenesLocal.add({
      id: "11111111-1111-1111-1111-111111111111", contrato_id: 1, equipo_serie: "RO-1", tecnico_id: 1,
      tipo_intervencion: "PREVENTIVO", fecha_creacion_cliente: "2026-01-01T00:00:00Z",
      lecturas_agua: { tds_entrada_ppm: 1, tds_post_membrana_ppm: 1, tds_producto_final_ppm: 1, ph: 7,
                       conductividad_us_cm: 1, resistividad_mohm_cm: 1, litros_consumidos_red: 1, litros_agua_pura: 1 },
      firma_base64: "AAAA", gps_latitud: -8, gps_longitud: -79, repuestos_consumidos: [],
      estado_sync: "pendiente", creado_en_local: "2026-01-01T00:00:00Z", intentos_sync: 0,
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if ((init?.method ?? "GET") === "POST") return new Response(JSON.stringify({ id: "x" }), { status: 201 });
      return new Response(JSON.stringify([]), { status: 200 }); // clientes/equipos/contratos: sin datos
    });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /sincronizar ahora/i }));
    await waitFor(async () =>
      expect((await db.ordenesLocal.get("11111111-1111-1111-1111-111111111111"))?.estado_sync).toBe("sincronizada"),
    );
  });
});
