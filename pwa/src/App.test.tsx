import { describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
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

  it("un equipo sin contrato asignado no se puede elegir (evita un contrato_id nulo en la orden)", async () => {
    await db.sesion.put({ id: "actual", token: "tok-ya-logueado", guardado_en: "2026-01-01" });
    await db.catalogoLocal.add({ id: "SIN-CONTRATO", tipo: "equipo", datos: { serie: "SIN-CONTRATO", contrato_id: null }, actualizado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    render(<App />);
    await screen.findByRole("heading", { name: /elegir equipo/i });
    const boton = await screen.findByRole("button", { name: "SIN-CONTRATO" });
    expect(boton).toBeDisabled();
  });

  it("la pantalla de stock movil tiene un boton para volver", async () => {
    await db.sesion.put({ id: "actual", token: "tok-ya-logueado", guardado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /stock móvil/i }));
    expect(await screen.findByRole("heading", { name: /stock móvil/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /volver/i }));
    expect(await screen.findByRole("heading", { name: /elegir equipo/i })).toBeInTheDocument();
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

  it("al entrar en la orden de un equipo permite volver al selector mediante el botón volver", async () => {
    await db.sesion.put({ id: "actual", token: "tok-ya-logueado", guardado_en: "2026-01-01" });
    await db.catalogoLocal.add({ id: "EQ-TEST-01", tipo: "equipo", datos: { serie: "EQ-TEST-01", contrato_id: 10 }, actualizado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "EQ-TEST-01" }));
    expect(await screen.findByRole("heading", { name: /lecturas de agua/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /volver a equipos/i }));
    expect(await screen.findByRole("heading", { name: /elegir equipo/i })).toBeInTheDocument();
  });

  it("la barra de navegación inferior permite cambiar a mis órdenes y regresar a equipos", async () => {
    await db.sesion.put({ id: "actual", token: "tok-ya-logueado", guardado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    render(<App />);
    const nav = await screen.findByRole("navigation", { name: /navegación móvil/i });
    const btnMisOrdenes = within(nav).getByRole("button", { name: /mis órdenes/i });
    await userEvent.click(btnMisOrdenes);
    expect(await screen.findByRole("heading", { name: /mis órdenes/i })).toBeInTheDocument();
    const btnEquipos = within(nav).getByRole("button", { name: /equipos/i });
    await userEvent.click(btnEquipos);
    expect(await screen.findByRole("heading", { name: /elegir equipo/i })).toBeInTheDocument();
  });

  it("al saltar a Equipos tras varios pasos, retrocede el historial nativo en vez de acumular otra entrada (evita que el botón atrás se trabe)", async () => {
    await db.sesion.put({ id: "actual", token: "tok-ya-logueado", guardado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    const goSpy = vi.spyOn(window.history, "go").mockImplementation(() => {});
    const pushSpy = vi.spyOn(window.history, "pushState");

    render(<App />);
    const nav = await screen.findByRole("navigation", { name: /navegación móvil/i });

    await userEvent.click(within(nav).getByRole("button", { name: /mis órdenes/i }));
    await screen.findByRole("heading", { name: /mis órdenes/i });
    await userEvent.click(within(nav).getByRole("button", { name: /stock móvil/i }));
    await screen.findByRole("heading", { name: /stock móvil/i });

    pushSpy.mockClear();

    await userEvent.click(within(nav).getByRole("button", { name: /equipos/i }));
    expect(await screen.findByRole("heading", { name: /elegir equipo/i })).toBeInTheDocument();

    // Debe retroceder exactamente los 2 pasos acumulados en el historial nativo,
    // en vez de apilar una entrada nueva encima (lo que desincroniza la pila y traba el botón atrás)
    expect(goSpy).toHaveBeenCalledWith(-2);
    expect(pushSpy).not.toHaveBeenCalled();

    goSpy.mockRestore();
    pushSpy.mockRestore();
  });

  it("resguarda el historial nativo al montar y lo vuelve a armar al llegar a la raíz, para que el botón Atrás nunca cierre la app (solo «Salir» debe hacerlo)", async () => {
    await db.sesion.put({ id: "actual", token: "tok-ya-logueado", guardado_en: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    const pushSpy = vi.spyOn(window.history, "pushState");

    render(<App />);
    await screen.findByRole("heading", { name: /elegir equipo/i });

    // Al montar, ya debe existir una entrada de resguardo aunque el usuario no haya navegado aún
    expect(pushSpy).toHaveBeenCalled();
    pushSpy.mockClear();

    // Simula el botón Atrás nativo mientras seguimos en la pantalla raíz (equipo): no hay nada
    // que desapilar dentro de la app, así que debe re-armar el resguardo en vez de dejar que
    // Android agote el historial y cierre la app
    act(() => {
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(pushSpy).toHaveBeenCalled();
    expect(await screen.findByRole("heading", { name: /elegir equipo/i })).toBeInTheDocument();

    pushSpy.mockRestore();
  });
});
