import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LiquidacionPage } from "./LiquidacionPage";
import { mockApi, renderWithProviders } from "../../test/utils";

const ID = "11111111-1111-1111-1111-111111111111";
const ORDEN = {
  id: ID,
  contrato_id: 1,
  equipo_serie: "RO-1",
  tecnico_id: 2,
  tipo_intervencion: "PREVENTIVO",
  estado: "COMPROMETIDA",
  fecha_creacion_cliente: "2026-03-01T09:00:00Z",
  fecha_sincronizacion: "2026-03-01T10:00:00Z",
  tiempo_respuesta_horas: "2.50",
};
const posts = (f: ReturnType<typeof mockApi>) =>
  f.mock.calls.filter(([, i]) => (i as RequestInit | undefined)?.method === "POST");
const urls = (f: ReturnType<typeof mockApi>) => f.mock.calls.map(([u]) => String(u));

describe("LiquidacionPage", () => {
  it("lista órdenes con su estado", async () => {
    mockApi([{ path: "/api/v1/ordenes", body: [ORDEN] }]);
    renderWithProviders(<LiquidacionPage />);
    expect(await screen.findByText("RO-1")).toBeInTheDocument();
    expect(screen.getByText("COMPROMETIDA", { selector: "span" }).closest("td")).toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/ordenes", body: [] }]);
    renderWithProviders(<LiquidacionPage />);
    expect(await screen.findByText("Sin datos disponibles")).toBeInTheDocument();
  });

  it("el filtro de estado consulta la API con ?estado=", async () => {
    const f = mockApi([{ path: /\/api\/v1\/ordenes/, body: [ORDEN] }]);
    renderWithProviders(<LiquidacionPage />);
    await screen.findByText("RO-1");
    await userEvent.selectOptions(screen.getByLabelText("Estado"), "LIQUIDADA");
    await vi.waitFor(() => expect(urls(f)).toContain("/api/v1/ordenes?estado=LIQUIDADA"));
  });

  it("liquidar pide confirmación y llama al endpoint (RN-03 fase 2)", async () => {
    const f = mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { method: "POST", path: `/api/v1/ordenes/${ID}/liquidar`, body: { ...ORDEN, estado: "LIQUIDADA" } },
    ]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /liquidar/i }));
    await vi.waitFor(() => expect(posts(f)).toHaveLength(1));
  });

  it("si se cancela la confirmación no se liquida", async () => {
    const f = mockApi([{ path: "/api/v1/ordenes", body: [ORDEN] }]);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /liquidar/i }));
    expect(posts(f)).toHaveLength(0);
  });

  it("una orden LIQUIDADA no ofrece liquidar pero sí adenda", async () => {
    mockApi([{ path: "/api/v1/ordenes", body: [{ ...ORDEN, estado: "LIQUIDADA" }] }]);
    renderWithProviders(<LiquidacionPage />);
    await screen.findByText("RO-1");
    expect(screen.queryByRole("button", { name: /^liquidar$/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /nota administrativa de corrección/i })).toBeInTheDocument();
  });

  it("muestra el error si liquidar falla (409)", async () => {
    mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { method: "POST", path: `/api/v1/ordenes/${ID}/liquidar`, status: 409, body: { detail: "La orden ya está liquidada" } },
    ]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /liquidar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La orden ya está liquidada");
  });

  it("emite una adenda con observación y ajuste de repuestos (RN-04)", async () => {
    const f = mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { path: `/api/v1/ordenes/${ID}/adendas`, body: [] },
      { method: "POST", path: `/api/v1/ordenes/${ID}/adendas`, status: 201, body: {} },
    ]);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nota administrativa de corrección/i }));
    await userEvent.type(screen.getByLabelText("Observación"), "Se usaron 3 filtros");
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/ajuste de cantidad/i), "-1");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await vi.waitFor(() => expect(posts(f)).toHaveLength(1));
    expect(JSON.parse((posts(f)[0][1] as RequestInit).body as string)).toEqual({
      observacion: "Se usaron 3 filtros",
      ajuste_repuestos: [{ repuesto_codigo: "FILT-05", delta: -1 }],
    });
  });

  it("adenda sin ajuste no envía ajuste_repuestos", async () => {
    const f = mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { path: `/api/v1/ordenes/${ID}/adendas`, body: [] },
      { method: "POST", path: `/api/v1/ordenes/${ID}/adendas`, status: 201, body: {} },
    ]);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nota administrativa de corrección/i }));
    await userEvent.type(screen.getByLabelText("Observación"), "Nota");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await vi.waitFor(() => expect(posts(f)).toHaveLength(1));
    expect(JSON.parse((posts(f)[0][1] as RequestInit).body as string)).toEqual({ observacion: "Nota" });
  });

  it.each([
    ["observación en blanco", "  ", "", "", /observación es obligatoria/i],
    ["ajuste sin código", "Nota", "", "2", /indica el código/i],
    ["código sin ajuste", "Nota", "FILT-05", "", /entero distinto de 0/i],
    ["ajuste 0", "Nota", "FILT-05", "0", /entero distinto de 0/i],
    ["ajuste decimal", "Nota", "FILT-05", "1.5", /entero distinto de 0/i],
  ])("adenda inválida: %s", async (_n, obs, cod, delta, msg) => {
    const f = mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { path: `/api/v1/ordenes/${ID}/adendas`, body: [] },
    ]);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nota administrativa de corrección/i }));
    await userEvent.type(screen.getByLabelText("Observación"), obs);
    if (cod) await userEvent.type(screen.getByLabelText(/código de repuesto/i), cod);
    if (delta) await userEvent.type(screen.getByLabelText(/ajuste de cantidad/i), delta);
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(msg)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("muestra el acta en solo lectura al abrir la adenda", async () => {
    mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { path: `/api/v1/ordenes/${ID}/adendas`, body: [] },
      {
        path: `/api/v1/ordenes/${ID}/acta`,
        body: {
          orden_id: ID,
          payload_raw: "hello",
          hash_sha256: "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
          previous_hash: null,
          firma_base64: "AAAA",
          gps_latitud: "-8.1116000",
          gps_longitud: "-79.0288000",
          creado_en: "2026-03-01T10:00:00Z",
        },
      },
    ]);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nota administrativa de corrección/i }));
    expect(await screen.findByText(/integridad verificada \(ley n° 27269\)/i)).toBeInTheDocument();
    expect(screen.getByText("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824").closest("details")).not.toHaveProperty("open", true);
    expect(screen.getByRole("img", { name: /firma registrada en el acta/i })).toHaveAttribute("src", "data:image/png;base64,AAAA");
    expect(screen.getByText(/-8\.11160, -79\.02880/)).toBeInTheDocument();
    expect(screen.getByText(/emitir nota administrativa de corrección/i)).toBeInTheDocument();
    await userEvent.click(screen.getByText(/ver detalles técnicos de auditoría/i));
    expect(screen.getByText("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar acta/i })).not.toBeInTheDocument();
  });

  it("no declara integridad verificada si el hash no coincide con el payload", async () => {
    mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { path: `/api/v1/ordenes/${ID}/adendas`, body: [] },
      { path: `/api/v1/ordenes/${ID}/acta`, body: {
        orden_id: ID, payload_raw: "contenido alterado", hash_sha256: "a".repeat(64), previous_hash: null,
        firma_base64: "AAAA", gps_latitud: "-8.1116000", gps_longitud: "-79.0288000", creado_en: "2026-03-01T10:00:00Z",
      } },
    ]);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nota administrativa de corrección/i }));
    expect(await screen.findByText("Integridad no verificada")).toBeInTheDocument();
    expect(screen.queryByText(/integridad verificada \(ley n° 27269\)/i)).not.toBeInTheDocument();
  });

  it("si la orden no tiene acta aún, lo indica sin romper el panel de adenda", async () => {
    mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { path: `/api/v1/ordenes/${ID}/adendas`, body: [] },
      { path: `/api/v1/ordenes/${ID}/acta`, status: 404, body: { detail: "La orden aún no tiene acta sincronizada" } },
    ]);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nota administrativa de corrección/i }));
    expect(await screen.findByText(/sin acta sincronizada/i)).toBeInTheDocument();
  });

  it("muestra las adendas previas de la orden", async () => {
    mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { path: `/api/v1/ordenes/${ID}/adendas`, body: [{ id: 1, orden_id: ID, gerente_id: 1, observacion: "Corrección previa", ajuste_repuestos: null, fecha_adenda: "2026-03-02T10:00:00Z" }] },
    ]);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nota administrativa de corrección/i }));
    expect(await screen.findByText(/Corrección previa/)).toBeInTheDocument();
  });

  it("muestra el 409 del backend si el ajuste excede el stock", async () => {
    mockApi([
      { path: "/api/v1/ordenes", body: [ORDEN] },
      { path: `/api/v1/ordenes/${ID}/adendas`, body: [] },
      { method: "POST", path: `/api/v1/ordenes/${ID}/adendas`, status: 409, body: { detail: "FILT-05: stock 2, se piden 5" } },
    ]);
    renderWithProviders(<LiquidacionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nota administrativa de corrección/i }));
    await userEvent.type(screen.getByLabelText("Observación"), "x");
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/ajuste de cantidad/i), "-5");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("stock 2, se piden 5");
  });
});
