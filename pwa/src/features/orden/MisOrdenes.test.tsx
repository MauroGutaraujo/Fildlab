import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MisOrdenes } from "./MisOrdenes";
import { db } from "../../db/dexie";
import { guardarSesionTurno } from "../../auth/session";
import { tokenDeTecnico } from "../../test/token";
import { procesarOutbox } from "../../db/outbox";
import { vi } from "vitest";
import { act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { cerrarSesion } from "../../auth/session";

const ORDEN_BASE = {
  contrato_id: 1, equipo_serie: "RO-1", tecnico_id: 1, tipo_intervencion: "PREVENTIVO",
  fecha_creacion_cliente: "2026-03-01T10:00:00Z",
  lecturas_agua: { tds_entrada_ppm: 1, tds_post_membrana_ppm: 1, tds_producto_final_ppm: 1, ph: 7,
                   conductividad_us_cm: 1, resistividad_mohm_cm: 1, litros_consumidos_red: 1, litros_agua_pura: 1 },
  firma_base64: "AAAA", gps_latitud: -8, gps_longitud: -79, repuestos_consumidos: [], intentos_sync: 0,
};
const BLOQUEADA = { ...ORDEN_BASE, id: "33333333-3333-4333-8333-333333333333", estado_sync: "error" as const,
  error_status: 409, error_detalle: "Stock insuficiente", creado_en_local: "2026-03-01T10:00:00Z" };

function conProvider(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("MisOrdenes", () => {
  it("descarga sólo el JSON original de la orden propia sin tokens ni alterar el UUID", async () => {
    const token = tokenDeTecnico(1, 1);
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Sin conexión"));
    await guardarSesionTurno(token);
    await db.ordenesLocal.bulkAdd([BLOQUEADA, { ...BLOQUEADA, id: "ajena", tecnico_id: 2 }]);
    let archivo: Blob | undefined;
    vi.stubGlobal("URL", class extends URL {
      static createObjectURL(blob: Blob) { archivo = blob; return "blob:acta"; }
      static revokeObjectURL() {}
    });
    const descargar = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe(`orden-${BLOQUEADA.id}.json`);
      expect(this.href).toBe("blob:acta");
    });
    conProvider(<MisOrdenes tecnicoId={1} />);
    const botones = await screen.findAllByRole("button", { name: /exportar json/i });
    expect(botones).toHaveLength(1);
    expect(descargar).not.toHaveBeenCalled();
    await userEvent.click(botones[0]);
    await waitFor(() => expect(descargar).toHaveBeenCalledTimes(1));
    const contenido = await new Promise<string>((resolve) => {
      const lector = new FileReader(); lector.onload = () => resolve(String(lector.result)); lector.readAsText(archivo!);
    });
    expect(JSON.parse(contenido)).toEqual(BLOQUEADA);
    expect(contenido).not.toContain(token);
    expect(contenido).not.toContain("ajena");
    expect(fetch).not.toHaveBeenCalled();
    expect(await db.ordenesLocal.get(BLOQUEADA.id)).toEqual(BLOQUEADA);
  });

  it.each([403, 404, 409])("reintenta un error %i por acción explícita sin cambiar el acta", async (status) => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add({ ...BLOQUEADA, error_status: status });
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ id: BLOQUEADA.id }), { status: 201 }));
    conProvider(<MisOrdenes tecnicoId={1} />);
    const reintentar = await screen.findByRole("button", { name: /reintentar envío/i });
    expect(fetch).not.toHaveBeenCalled();
    await userEvent.click(reintentar);
    expect(await screen.findByText("Sincronizada")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    const payload = JSON.parse(fetch.mock.calls[0][1]?.body as string);
    expect(payload).toMatchObject({ id: BLOQUEADA.id, firma_base64: "AAAA", contrato_id: 1, lecturas_agua: ORDEN_BASE.lecturas_agua });
    expect((await db.ordenesLocal.get(BLOQUEADA.id))?.firma_base64).toBe("AAAA");
  });

  it("un rechazo repetido permanece visible y no se reintenta en bucle", async () => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add(BLOQUEADA);
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ detail: "Equipo no encontrado" }), { status: 404 }));
    conProvider(<MisOrdenes tecnicoId={1} />);
    await userEvent.click(await screen.findByRole("button", { name: /reintentar envío/i }));
    expect(await screen.findByText("Equipo no encontrado")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    await act(async () => { await procesarOutbox(); });
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("el 422 exige exportación y revisión y no ofrece reintento", async () => {
    await db.ordenesLocal.add({ ...BLOQUEADA, error_status: 422 });
    conProvider(<MisOrdenes tecnicoId={1} />);
    expect(await screen.findByRole("button", { name: /exportar json/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reintentar envío/i })).not.toBeInTheDocument();
    expect(screen.getByText(/requiere revisión/i)).toBeInTheDocument();
  });

  it.each(["exportar JSON", "reintentar envío"])("rechaza %s si la sesión cambió después de mostrar la lista", async (accion) => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add(BLOQUEADA);
    const fetch = vi.spyOn(globalThis, "fetch");
    conProvider(<MisOrdenes tecnicoId={1} />);
    const boton = await screen.findByRole("button", { name: new RegExp(accion, "i") });
    await guardarSesionTurno(tokenDeTecnico(2));
    await userEvent.click(boton);
    expect(await screen.findByRole("alert")).toHaveTextContent(/sesión|propietario/i);
    expect(await db.ordenesLocal.get(BLOQUEADA.id)).toEqual(BLOQUEADA);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("no pone en cola si se cerró la sesión", async () => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add(BLOQUEADA);
    conProvider(<MisOrdenes tecnicoId={1} />);
    const boton = await screen.findByRole("button", { name: /reintentar envío/i });
    await cerrarSesion();
    await userEvent.click(boton);
    expect(await screen.findByRole("alert")).toHaveTextContent(/sesión/i);
    expect(await db.ordenesLocal.get(BLOQUEADA.id)).toEqual(BLOQUEADA);
  });

  it("muestra un error visible si el navegador no puede descargar el archivo", async () => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add(BLOQUEADA);
    vi.stubGlobal("URL", class extends URL { static createObjectURL(): string { throw new Error("Descarga no disponible"); } });
    conProvider(<MisOrdenes tecnicoId={1} />);
    await userEvent.click(await screen.findByRole("button", { name: /exportar json/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Descarga no disponible");
  });
  it("muestra 'sin ordenes' cuando no hay ninguna", async () => {
    conProvider(<MisOrdenes tecnicoId={1} />);
    expect(await screen.findByText(/no hay órdenes/i)).toBeInTheDocument();
  });

  it("lista las ordenes con su estado y el detalle del error si lo tiene", async () => {
    await db.ordenesLocal.bulkAdd([
      { ...ORDEN_BASE, id: "11111111-1111-1111-1111-111111111111", estado_sync: "pendiente", creado_en_local: "2026-03-01T10:00:00Z" },
      { ...ORDEN_BASE, id: "22222222-2222-2222-2222-222222222222", estado_sync: "error",
        error_detalle: "FILT-05: stock 2, se piden 5", creado_en_local: "2026-03-01T10:01:00Z" },
    ]);
    conProvider(<MisOrdenes tecnicoId={1} />);
    expect(await screen.findByText(/pendiente/i)).toBeInTheDocument();
    expect(await screen.findByText(/error/i)).toBeInTheDocument();
    expect(await screen.findByText(/stock 2, se piden 5/i)).toBeInTheDocument();
  });

  it("el técnico B sólo ve sus órdenes y no reutiliza la caché de A", async () => {
    await db.ordenesLocal.bulkAdd([
      { ...ORDEN_BASE, id: "acta-a", equipo_serie: "EQUIPO-A", estado_sync: "pendiente", creado_en_local: "2026-01-01" },
      { ...ORDEN_BASE, id: "acta-b", tecnico_id: 2, equipo_serie: "EQUIPO-B", estado_sync: "pendiente", creado_en_local: "2026-01-01" },
    ]);
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const vista = render(<QueryClientProvider client={qc}><MisOrdenes tecnicoId={1} /></QueryClientProvider>);
    expect(await screen.findByText("Equipo EQUIPO-A")).toBeInTheDocument();
    vista.rerender(<QueryClientProvider client={qc}><MisOrdenes tecnicoId={2} /></QueryClientProvider>);
    expect(screen.queryByText("Equipo EQUIPO-A")).not.toBeInTheDocument();
    expect(await screen.findByText("Equipo EQUIPO-B")).toBeInTheDocument();
  });

  it("refresca el estado después de una sincronización automática", async () => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add({ ...ORDEN_BASE, id: "auto", estado_sync: "pendiente", creado_en_local: "2026-01-01" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "auto" }), { status: 201 }));
    conProvider(<MisOrdenes tecnicoId={1} />);
    expect(await screen.findByText("Pendiente de sincronizar")).toBeInTheDocument();
    await act(async () => { await procesarOutbox(); });
    await waitFor(() => expect(screen.getByText("Sincronizada")).toBeInTheDocument());
  });
});
