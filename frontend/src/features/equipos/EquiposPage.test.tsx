import { describe, expect, it } from "vitest";
import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EquiposPage } from "./EquiposPage";
import { mockApi, renderWithProviders } from "../../test/utils";

// REQ-03: los 8 parámetros de referencia (TDS entrada/post-membrana/producto final,
// pH, conductividad, resistividad, litros de red y litros de agua pura).
const PARAMS_REQ03 = {
  tds_entrada_ppm: 350,
  tds_post_membrana_ppm: 8,
  tds_producto_final_ppm: 5,
  ph: 7.0,
  conductividad_us_cm: 15,
  resistividad_mohm_cm: 1.2,
  litros_consumidos_red: 500,
  litros_agua_pura: 420,
};

const EQUIPO = {
  serie: "RO-2026-0001",
  cliente_ruc: "20612493821",
  contrato_id: null,
  tipo_sistema: "OSMOSIS_INVERSA",
  fecha_instalacion: "2026-01-15",
  parametros_nominales: PARAMS_REQ03,
};

const SIN_PREDICCIONES = { path: "/api/v1/equipos/predicciones-rul", body: [] };

const posts = (f: ReturnType<typeof mockApi>) =>
  f.mock.calls.filter(([, i]) => (i as RequestInit | undefined)?.method === "POST");

const LABELS_PARAMS: Record<keyof typeof PARAMS_REQ03, RegExp> = {
  tds_entrada_ppm: /tds entrada/i,
  tds_post_membrana_ppm: /tds post-membrana/i,
  tds_producto_final_ppm: /tds producto final/i,
  ph: /^ph$/i,
  conductividad_us_cm: /conductividad/i,
  resistividad_mohm_cm: /resistividad/i,
  litros_consumidos_red: /litros consumidos/i,
  litros_agua_pura: /litros de agua pura/i,
};

async function llenar(
  o: { serie?: string; ruc?: string; fecha?: string; params?: Partial<typeof PARAMS_REQ03>; tipo?: string } = {},
) {
  await userEvent.type(screen.getByLabelText("Serie"), o.serie ?? "RO-1");
  await userEvent.type(screen.getByLabelText(/RUC del cliente/i), o.ruc ?? "20612493821");
  if (o.tipo) await userEvent.selectOptions(screen.getByLabelText("Tipo de sistema"), o.tipo);
  fireEvent.change(screen.getByLabelText(/fecha de instalación/i), { target: { value: o.fecha ?? "2026-01-15" } });
  const valores = { ...PARAMS_REQ03, ...o.params };
  for (const [campo, regex] of Object.entries(LABELS_PARAMS)) {
    fireEvent.change(screen.getByLabelText(regex), { target: { value: String(valores[campo as keyof typeof PARAMS_REQ03]) } });
  }
}

describe("EquiposPage", () => {
  it("lista equipos con su tipo legible y parámetros", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    expect(await screen.findByText("RO-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Ósmosis inversa")).toBeInTheDocument();
    expect(screen.queryByText(/tds_entrada_ppm/)).not.toBeInTheDocument();
    expect(screen.getByText("TDS: 350 ppm")).toBeInTheDocument();
    expect(screen.getByText("TDS post: 8 ppm")).toBeInTheDocument();
    expect(screen.getByText("pH: 7")).toBeInTheDocument();
  });

  it("el detalle de parámetros nominales se ve en un modal, con etiquetas legibles", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    await screen.findByText("RO-2026-0001");
    expect(screen.queryByText("TDS entrada (ppm)")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /ver detalle/i }));
    const dialog = await screen.findByRole("dialog", { name: /parámetros nominales/i });
    expect(within(dialog).getByText("TDS entrada: 350 ppm")).toBeInTheDocument();
    expect(within(dialog).getByText("pH: 7")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /cerrar/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("TECNICO no ve acciones de escritura", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    await screen.findByText("RO-2026-0001");
    expect(screen.queryByRole("button", { name: /nuevo equipo/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    // El panel de riesgo RUL y la tabla de equipos comparten el mismo texto de vacío
    // (REQ-16) cuando ambos estan vacios a la vez — ambas ocurrencias son legitimas.
    const mensajes = await screen.findAllByText("Sin datos disponibles");
    expect(mensajes.length).toBeGreaterThanOrEqual(1);
  });

  it("ofrece los tres tipos de sistema", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    const opciones = Array.from((screen.getByLabelText("Tipo de sistema") as HTMLSelectElement).options).map((o) => o.value);
    expect(opciones).toEqual(["OSMOSIS_INVERSA", "ABLANDADOR", "FILTRO"]);
  });

  it("crea un equipo con el body que espera la API", async () => {
    const f = mockApi([
      { path: "/api/v1/equipos", body: [] },
      SIN_PREDICCIONES,
      { method: "POST", path: "/api/v1/equipos", status: 201, body: EQUIPO },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar({ tipo: "ABLANDADOR" });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nuevo equipo/i });
    expect(JSON.parse((posts(f)[0][1] as RequestInit).body as string)).toEqual({
      serie: "RO-1",
      cliente_ruc: "20612493821",
      tipo_sistema: "ABLANDADOR",
      fecha_instalacion: "2026-01-15",
      parametros_nominales: PARAMS_REQ03,
    });
  });

  it("parámetros nominales: un campo vacío se rechaza", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    fireEvent.change(screen.getByLabelText(/tds entrada/i), { target: { value: "" } });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/valor numérico/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("parámetros nominales: un texto no numérico se rechaza", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    fireEvent.change(screen.getByLabelText(/conductividad/i), { target: { value: "abc" } });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/valor numérico/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("parámetros nominales: pH fuera de 0-14 se rechaza", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar({ params: { ph: 15 } });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/valor máximo es 14/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("rechaza serie vacía, RUC inválido y fecha futura", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar({ serie: " ", ruc: "123", fecha: "2999-01-01" });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/serie es obligatoria/i)).toBeInTheDocument();
    expect(screen.getByText(/exactamente 11 dígitos/i)).toBeInTheDocument();
    expect(screen.getByText(/no puede ser futura/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("muestra el 409 de serie duplicada", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [] },
      SIN_PREDICCIONES,
      { method: "POST", path: "/api/v1/equipos", status: 409, body: { detail: "Ya existe un equipo con esa serie" } },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe un equipo con esa serie");
  });

  it("equipo sin predicción muestra el badge «Sin evaluar»", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("Sin evaluar")).toBeInTheDocument();
  });

  it("equipo con predicción ROJO muestra el badge y el panel de alertas", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [{ equipo_serie: "RO-2026-0001", dias_vida_util_remanente: 12, nivel_alerta: "ROJO" }] },
    ]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText(/intervención urgente/i)).toBeInTheDocument();
    expect(screen.getByText(/riesgo crítico/i)).toBeInTheDocument();
    expect(screen.getByText(/RO-2026-0001 — 12 días restantes/i)).toBeInTheDocument();
  });

  it.each([
    [61, /óptimo/i],
    [60, /mantenimiento próximo/i],
    [15, /mantenimiento próximo/i],
    [14, /intervención urgente/i],
  ])("clasifica la vida útil remanente de %i días", async (dias, estado) => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [{ equipo_serie: EQUIPO.serie, dias_vida_util_remanente: dias, nivel_alerta: "VERDE" }] },
    ]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText(estado)).toBeInTheDocument();
  });

  it("etiqueta el filtro como sistema multimedia", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [{ ...EQUIPO, tipo_sistema: "FILTRO" }] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("Filtro multimedia")).toBeInTheDocument();
  });

  it("sin equipos en ROJO no muestra el panel de alertas", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [{ equipo_serie: "RO-2026-0001", dias_vida_util_remanente: 200, nivel_alerta: "VERDE" }] },
    ]);
    renderWithProviders(<EquiposPage />);
    await screen.findByText(/óptimo/i);
    expect(screen.getByText(/riesgo crítico/i)).toBeInTheDocument();
    expect(screen.getByText("Sin datos disponibles")).toBeInTheDocument();
  });

  it("si falla la consulta de predicciones, el panel avisa el error sin bloquear la tabla", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", status: 500, body: { detail: "Error interno" } },
    ]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("RO-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Sin evaluar")).toBeInTheDocument();
    expect(await screen.findByText(/no se pudieron cargar las predicciones/i)).toBeInTheDocument();
  });

  it("GERENCIA puede marcar un equipo como mantenido, y ve la confirmación", async () => {
    const f = mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      SIN_PREDICCIONES,
      { method: "POST", path: "/api/v1/equipos/RO-2026-0001/marcar-mantenimiento", body: { ...EQUIPO, fecha_ultima_mantencion: "2026-10-09" } },
    ]);
    renderWithProviders(<EquiposPage />);
    await screen.findByText("RO-2026-0001");
    await userEvent.click(screen.getByRole("button", { name: /marcar mantenimiento/i }));
    expect(await screen.findByText(/registrado/i)).toBeInTheDocument();
    const llamadas = f.mock.calls.map(([u, i]) => `${(i as RequestInit | undefined)?.method ?? "GET"} ${String(u)}`);
    expect(llamadas).toContain("POST /api/v1/equipos/RO-2026-0001/marcar-mantenimiento");
  });

  it("TECNICO no ve el botón de marcar mantenimiento", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    await screen.findByText("RO-2026-0001");
    expect(screen.queryByRole("button", { name: /marcar mantenimiento/i })).not.toBeInTheDocument();
  });
});
