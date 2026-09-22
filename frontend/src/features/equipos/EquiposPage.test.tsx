import { describe, expect, it } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
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

const posts = (f: ReturnType<typeof mockApi>) =>
  f.mock.calls.filter(([, i]) => (i as RequestInit | undefined)?.method === "POST");

async function llenar(o: { serie?: string; ruc?: string; fecha?: string; params?: string; tipo?: string } = {}) {
  await userEvent.type(screen.getByLabelText("Serie"), o.serie ?? "RO-1");
  await userEvent.type(screen.getByLabelText(/RUC del cliente/i), o.ruc ?? "20612493821");
  if (o.tipo) await userEvent.selectOptions(screen.getByLabelText("Tipo de sistema"), o.tipo);
  fireEvent.change(screen.getByLabelText(/fecha de instalación/i), { target: { value: o.fecha ?? "2026-01-15" } });
  fireEvent.change(screen.getByLabelText(/parámetros nominales/i), { target: { value: o.params ?? JSON.stringify(PARAMS_REQ03) } });
}

describe("EquiposPage", () => {
  it("lista equipos con su tipo legible y parámetros", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    expect(await screen.findByText("RO-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Ósmosis inversa")).toBeInTheDocument();
    expect(screen.getByText(/tds_entrada_ppm/)).toBeInTheDocument();
  });

  it("TECNICO no ve acciones de escritura", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [EQUIPO] }]);
    renderWithProviders(<EquiposPage />, { rol: "TECNICO" });
    await screen.findByText("RO-2026-0001");
    expect(screen.queryByRole("button", { name: /nuevo equipo/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [] }]);
    renderWithProviders(<EquiposPage />);
    expect(await screen.findByText("Sin datos disponibles")).toBeInTheDocument();
  });

  it("ofrece los tres tipos de sistema", async () => {
    mockApi([{ path: "/api/v1/equipos", body: [] }]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    const opciones = Array.from((screen.getByLabelText("Tipo de sistema") as HTMLSelectElement).options).map((o) => o.value);
    expect(opciones).toEqual(["OSMOSIS_INVERSA", "ABLANDADOR", "FILTRO"]);
  });

  it("crea un equipo con el body que espera la API", async () => {
    const f = mockApi([
      { path: "/api/v1/equipos", body: [] },
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

  it.each([
    ["JSON inválido", "{presion:", /objeto JSON/i],
    ["objeto vacío", "{}", /objeto JSON/i],
    ["un arreglo", "[1,2]", /objeto JSON/i],
  ])("parámetros nominales: %s se rechaza", async (_n, params, msg) => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar({ params });
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(msg)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("rechaza serie vacía, RUC inválido y fecha futura", async () => {
    const f = mockApi([{ path: "/api/v1/equipos", body: [] }]);
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
      { method: "POST", path: "/api/v1/equipos", status: 409, body: { detail: "Ya existe un equipo con esa serie" } },
    ]);
    renderWithProviders(<EquiposPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo equipo/i }));
    await llenar();
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe un equipo con esa serie");
  });
});
