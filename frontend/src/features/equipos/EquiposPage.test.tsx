import { describe, expect, it } from "vitest";
import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EquiposPage } from "./EquiposPage";
import { mockApi as mockApiBase, renderWithProviders } from "../../test/utils";

function mockApi(rutas:Parameters<typeof mockApiBase>[0]) {
  return mockApiBase([{path:"/api/v1/equipos/supervision-rul",body:{estado:"NORMAL",avisos:[],consultado_en:"2026-10-22T15:00:00Z",
    ultima_exitosa_en:"2026-10-22T08:00:00Z",total_equipos:1,equipos_sin_evaluar:0,ejecuciones_sin_cierre:0}},...rutas]);
}

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
const PREDICCION = {
  equipo_serie: EQUIPO.serie, dias_vida_util_remanente: 12, nivel_alerta: "ROJO",
  actualizado_en: "2026-10-22T15:00:00Z", version_calculo: "COX_INSTALACION_V3", version_dataset: "WEIBULL_CENSURA_V2",
  fecha_referencia: "2026-01-15", alcance_estimacion: "SISTEMA_DESDE_INSTALACION",
  motivo_no_estimable: null, estado_estimacion: "ESTIMADA", experimental: true,
  origen_datos: "SINTETICOS", politica_alerta: "RUL_30_90_V1",
  vence_en: "2099-01-01T00:00:00Z", ejecucion_id: "run-1", tipo_referencia: "OSMOSIS_INVERSA",
};
const CONTRATO = { id: 7, cliente_ruc: EQUIPO.cliente_ruc, estado: "ACTIVO", fecha_inicio: "2026-01-01", fecha_fin: "2026-12-31" };
const CONTRATOS = { path: `/api/v1/contratos?cliente_ruc=${EQUIPO.cliente_ruc}`, body: [CONTRATO] };

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

  it("el botón «Ver ejecuciones de IA» sigue visible con el formulario de nuevo equipo abierto", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /^ver ejecuciones de ia$/i }));
    expect(screen.getByRole("button", { name: /^ocultar ejecuciones de ia$/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^nuevo equipo$/i }));
    expect(screen.getByRole("button", { name: /^ocultar ejecuciones de ia$/i })).toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
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
      CONTRATOS,
      { method: "POST", path: "/api/v1/equipos", status: 201, body: EQUIPO },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar({ tipo: "ABLANDADOR" });
    await userEvent.selectOptions(await screen.findByLabelText("Contrato del cliente"), "7");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nuevo equipo/i });
    expect(JSON.parse((posts(f)[0][1] as RequestInit).body as string)).toEqual({
      serie: "RO-1",
      cliente_ruc: "20612493821",
      contrato_id: 7,
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
      CONTRATOS,
      { method: "POST", path: "/api/v1/equipos", status: 409, body: { detail: "Ya existe un equipo con esa serie" } },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    await userEvent.selectOptions(await screen.findByLabelText("Contrato del cliente"), "7");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe un equipo con esa serie");
  });

  it("permite asociar un equipo legado sin contrato sin reemplazar sus parámetros", async () => {
    const f = mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES, CONTRATOS,
      { method: "PUT", path: `/api/v1/equipos/${EQUIPO.serie}`, body: { ...EQUIPO, contrato_id: 7 } },
    ]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("Sin contrato")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /editar contrato/i }));
    expect(screen.getByLabelText(/RUC del cliente/i)).toBeDisabled();
    await screen.findByRole("option", { name: /Contrato #7/ });
    await userEvent.selectOptions(screen.getByLabelText("Contrato del cliente"), "7");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nuevo equipo/i });
    const put = f.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(JSON.parse(put?.[1]?.body as string)).toEqual({ contrato_id: 7 });
  });

  it("filtra contratos ajenos y anulados y limpia selección al cambiar cliente", async () => {
    const f = mockApi([
      { path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES,
      { ...CONTRATOS, body: [CONTRATO, { ...CONTRATO, id: 8, estado: "ANULADO" }, { ...CONTRATO, id: 9, cliente_ruc: "20111111111" }] },
      { path: "/api/v1/contratos?cliente_ruc=20111111111", body: [] },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    await screen.findByRole("option", { name: /Contrato #7/ });
    const selector = screen.getByLabelText("Contrato del cliente");
    expect(within(selector).getAllByRole("option")).toHaveLength(2);
    await userEvent.selectOptions(selector, "7");
    fireEvent.change(screen.getByLabelText(/RUC del cliente/i), { target: { value: "20111111111" } });
    expect(selector).toHaveValue("");
    expect(await screen.findByText(/no hay contratos disponibles/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(posts(f)).toHaveLength(0);
    expect(await screen.findByText(/selecciona un contrato válido/i)).toBeInTheDocument();
  });

  it("impide crear sin contrato seleccionado", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES, CONTRATOS]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    await screen.findByRole("option", { name: /Contrato #7/ });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/selecciona un contrato válido/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("muestra errores al cargar contratos y permite reintentar", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }, SIN_PREDICCIONES,
      { ...CONTRATOS, status: 503, body: { detail: "Servicio no disponible" } },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    expect(await screen.findByText(/no se pudieron cargar los contratos/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Contrato del cliente")).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /reintentar contratos/i }));
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(posts(f)).toHaveLength(0);
    expect(f.mock.calls.filter(([url]) => url === CONTRATOS.path).length).toBeGreaterThanOrEqual(2);
  });

  it("bloquea la asociación mientras se cargan contratos", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    const responder = f.getMockImplementation()!;
    f.mockImplementation((input, init) => String(input) === CONTRATOS.path
      ? new Promise<Response>(() => {}) : responder(input, init));
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /editar contrato/i }));
    expect(await screen.findByRole("status")).toHaveTextContent("Cargando contratos");
    expect(screen.getByLabelText("Contrato del cliente")).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(f.mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(0);
  });

  it("conserva el formulario y muestra el rechazo al asociar contrato", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES, CONTRATOS,
      { method: "PUT", path: `/api/v1/equipos/${EQUIPO.serie}`, status: 422, body: { detail: "El contrato está anulado" } },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /editar contrato/i }));
    await screen.findByRole("option", { name: /Contrato #7/ });
    await userEvent.selectOptions(screen.getByLabelText("Contrato del cliente"), "7");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El contrato está anulado");
    expect(screen.getByLabelText("Contrato del cliente")).toHaveValue("7");
    expect(screen.getByText("Sin contrato")).toBeInTheDocument();
  });

  it("equipo sin predicción muestra el badge «Sin evaluar»", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("Sin evaluar")).toBeInTheDocument();
  });

  it("equipo con predicción ROJO muestra el badge y el panel de alertas", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [PREDICCION] },
    ]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText(/prioridad experimental alta/i)).toBeInTheDocument();
    expect(screen.getByText(/RO-2026-0001 — 12 días estimados/i)).toBeInTheDocument();
    expect(screen.queryByText(/estimación experimental basada en datos sintéticos/i)).not.toBeInTheDocument();
    expect(screen.getByText(/22\/10\/2026/)).toHaveAttribute("datetime", "2026-10-22T15:00:00Z");
  });

  it.each([
    [29, "ROJO", /prioridad experimental alta/i],
    [30, "AMARILLO", /prioridad experimental media/i],
    [89, "AMARILLO", /prioridad experimental media/i],
    [90, "VERDE", /prioridad experimental baja/i],
    // Pares deliberadamente discordantes: el cliente presenta el nivel del servidor.
    [75, "VERDE", /prioridad experimental baja/i],
    [20, "ROJO", /prioridad experimental alta/i],
  ])("presenta %i días con nivel %s del servidor", async (dias, nivel, estado) => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [{ ...PREDICCION, dias_vida_util_remanente: dias, nivel_alerta: nivel }] },
    ]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText(estado)).toBeInTheDocument();
    const lista = screen.queryByText(new RegExp(`${EQUIPO.serie} — ${dias} días estimados`));
    expect(lista !== null).toBe(nivel === "ROJO");
  });

  it("etiqueta el filtro como sistema multimedia", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [{ ...EQUIPO, tipo_sistema: "FILTRO" }] }, SIN_PREDICCIONES]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("Filtro multimedia")).toBeInTheDocument();
  });

  it("sin equipos en ROJO no muestra el panel de alertas", async () => {
    mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [{ ...PREDICCION, dias_vida_util_remanente: 200, nivel_alerta: "VERDE" }] },
    ]);
    renderWithProviders(<EquiposPage />);
    await screen.findByText(/prioridad experimental baja/i);
    expect(screen.getByText("Sin estimaciones de prioridad alta")).toBeInTheDocument();
  });

  it.each([
    ["REQUIERE_RECALCULO", "REQUIERE_RECALCULO", /recálculo pendiente/i],
    ["NO_ESTIMABLE", "MODELO_INESTABLE", /ajuste del modelo requiere revisión/i],
    ["NO_ESTIMABLE", "EDAD_FUERA_SOPORTE", /antigüedad supera/i],
  ])("muestra %s sin cifra ni prioridad", async (estado, motivo, texto) => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] },
      { path: "/api/v1/equipos/predicciones-rul", body: [{ ...PREDICCION,
        estado_estimacion: estado, motivo_no_estimable: motivo, dias_vida_util_remanente: null, nivel_alerta: null }] }]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText(texto)).toBeInTheDocument();
    expect(screen.queryByText(/prioridad experimental (alta|media|baja)/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/0 días/)).not.toBeInTheDocument();
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

  it("GERENCIA abre componentes y mantenimiento sin reiniciar la edad global", async () => {
    const f = mockApi([
      { path: "/api/v1/equipos", body: [EQUIPO] },
      SIN_PREDICCIONES,
      { path: "/api/v1/equipos/RO-2026-0001/componentes", body: [] },
    ]);
    renderWithProviders(<EquiposPage />);
    await screen.findByText("RO-2026-0001");
    await userEvent.click(screen.getByRole("button", { name: /componentes y mantenimiento/i }));
    expect(await screen.findByRole("dialog", { name: /componentes y mantenimiento/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /agregar componente/i })).toBeInTheDocument();
    expect(f.mock.calls.filter(([,init])=>init?.method === "POST")).toHaveLength(0);
  });

  it("TECNICO consulta componentes sin acciones de escritura", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }, SIN_PREDICCIONES,
      { path: "/api/v1/equipos/RO-2026-0001/componentes", body: [] }]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    await screen.findByText("RO-2026-0001");
    expect(screen.queryByRole("button", { name: /marcar mantenimiento/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /componentes y mantenimiento/i }));
    expect(await screen.findByRole("dialog", { name: /componentes y mantenimiento/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /agregar componente/i })).not.toBeInTheDocument();
  });
});
