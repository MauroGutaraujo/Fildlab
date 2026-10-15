import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InventarioPage } from "./InventarioPage";
import { mockApi, renderWithProviders } from "../../test/utils";

const REPUESTO = { codigo: "FILT-05", descripcion: "Filtro 5 micras", stock_almacen_central: 7, costo_unitario_soles: "12.50" };
const MOV = { id: 1, repuesto_codigo: "FILT-05", tipo: "ENTRADA", cantidad: 10, orden_id: null, venta_id: null, usuario_id: 1, creado_en: "2026-03-01T10:00:00Z" };
const base = [
  { path: "/api/v1/repuestos", body: [REPUESTO] },
  { path: "/api/v1/inventario/movimientos", body: [MOV] },
];
const posts = (f: ReturnType<typeof mockApi>) =>
  f.mock.calls.filter(([, i]) => (i as RequestInit | undefined)?.method === "POST");
const bodyOf = (call: unknown[]) => JSON.parse((call[1] as RequestInit).body as string);

async function abrirMovimiento() {
  await userEvent.click(await screen.findByRole("button", { name: /registrar movimiento/i }));
}

describe("InventarioPage", () => {
  it("muestra stock central y movimientos", async () => {
    mockApi(base);
    renderWithProviders(<InventarioPage />);
    const fila = (await screen.findByText("Filtro 5 micras")).closest("tr")!;
    expect(within(fila).getByText(/stock limitado/i)).toHaveTextContent("7");
    expect(await screen.findByRole("heading", { name: /historial de entradas y salidas/i })).toBeInTheDocument();
    expect(await screen.findByText("+10")).toBeInTheDocument();
  });

  it.each([
    [0, /agotado/i], [1, /stock bajo/i], [5, /stock bajo/i],
    [6, /stock limitado/i], [10, /stock limitado/i], [11, /saludable/i],
  ])("clasifica el stock %i con su semáforo", async (stock, estado) => {
    mockApi([
      { path: "/api/v1/repuestos", body: [{ ...REPUESTO, stock_almacen_central: stock }] },
      { path: "/api/v1/inventario/movimientos", body: [] },
    ]);
    renderWithProviders(<InventarioPage />);
    const fila = (await screen.findByText("Filtro 5 micras")).closest("tr")!;
    expect(within(fila).getByText(estado)).toBeInTheDocument();
  });

  it("formatea el costo peruano y separa catálogo del historial", async () => {
    mockApi(base);
    renderWithProviders(<InventarioPage />);
    expect(await screen.findByText("S/. 12.50")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /catálogo de repuestos/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /historial de entradas y salidas/i })).toBeInTheDocument();
  });

  it("TECNICO solo lee", async () => {
    mockApi(base);
    renderWithProviders(<InventarioPage />, { rol: "TECNICO" });
    await screen.findByText("Filtro 5 micras");
    expect(screen.queryByRole("button", { name: /nuevo repuesto/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /registrar movimiento/i })).not.toBeInTheDocument();
  });

  it("lista vacía muestra «Sin datos disponibles»", async () => {
    mockApi([{ path: "/api/v1/repuestos", body: [] }, { path: "/api/v1/inventario/movimientos", body: [] }]);
    renderWithProviders(<InventarioPage />);
    expect((await screen.findAllByText("Sin datos disponibles")).length).toBeGreaterThan(0);
  });

  it("crea un repuesto", async () => {
    const f = mockApi([...base, { method: "POST", path: "/api/v1/repuestos", status: 201, body: REPUESTO }]);
    renderWithProviders(<InventarioPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo repuesto/i }));
    await userEvent.type(screen.getByLabelText("Código"), "MEMB-01");
    await userEvent.type(screen.getByLabelText("Descripción"), "Membrana");
    await userEvent.type(screen.getByLabelText(/costo unitario/i), "99.90");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /nuevo repuesto/i });
    expect(bodyOf(posts(f)[0])).toEqual({ codigo: "MEMB-01", descripcion: "Membrana", costo_unitario_soles: "99.90" });
  });

  it.each(["-1", "abc", "1.234"])("costo «%s» se rechaza", async (costo) => {
    const f = mockApi(base);
    renderWithProviders(<InventarioPage />);
    await userEvent.click(await screen.findByRole("button", { name: /nuevo repuesto/i }));
    await userEvent.type(screen.getByLabelText("Código"), "X");
    await userEvent.type(screen.getByLabelText("Descripción"), "Y");
    await userEvent.type(screen.getByLabelText(/costo unitario/i), costo);
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/costo debe ser/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("registra una entrada de stock", async () => {
    const f = mockApi([...base, { method: "POST", path: "/api/v1/inventario/movimientos", status: 201, body: MOV }]);
    renderWithProviders(<InventarioPage />);
    await abrirMovimiento();
    await userEvent.selectOptions(screen.getByLabelText("Repuesto"), "FILT-05");
    await userEvent.type(screen.getByLabelText("Cantidad"), "5");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /registrar movimiento/i });
    expect(bodyOf(posts(f)[0])).toEqual({ repuesto_codigo: "FILT-05", tipo: "ENTRADA", cantidad: 5 });
  });

  it.each(["0", "-2", "1.5", ""])("cantidad «%s» se rechaza", async (cant) => {
    const f = mockApi(base);
    renderWithProviders(<InventarioPage />);
    await abrirMovimiento();
    await userEvent.selectOptions(screen.getByLabelText("Repuesto"), "FILT-05");
    if (cant) await userEvent.type(screen.getByLabelText("Cantidad"), cant);
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/cantidad debe ser un entero/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("exige elegir un repuesto", async () => {
    const f = mockApi(base);
    renderWithProviders(<InventarioPage />);
    await abrirMovimiento();
    await userEvent.type(screen.getByLabelText("Cantidad"), "1");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/elige un repuesto/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
  });

  it("salida por orden exige elegir la orden del desplegable y envía su UUID", async () => {
    const ORDEN_ID = "11111111-1111-1111-1111-111111111111";
    const f = mockApi([
      ...base,
      { path: "/api/v1/ordenes", body: [{ id: ORDEN_ID, contrato_id: 1, fecha_creacion_cliente: "2026-10-15T10:00:00Z" }] },
      { path: "/api/v1/contratos", body: [{ id: 1, cliente_ruc: "20612493821" }] },
      { path: "/api/v1/clientes", body: [{ ruc: "20612493821", razon_social: "CLINICA SANCHEZ FERRER" }] },
      { method: "POST", path: "/api/v1/inventario/movimientos", status: 201, body: MOV },
    ]);
    renderWithProviders(<InventarioPage />);
    await abrirMovimiento();
    await userEvent.selectOptions(screen.getByLabelText("Repuesto"), "FILT-05");
    await userEvent.selectOptions(screen.getByLabelText("Tipo de movimiento"), "SALIDA_ORDEN");
    await userEvent.type(screen.getByLabelText("Cantidad"), "1");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByText(/elegir la orden/i)).toBeInTheDocument();
    expect(posts(f)).toHaveLength(0);
    await screen.findByText(/OT-01CSF151026/);
    await userEvent.selectOptions(screen.getByLabelText("Orden"), ORDEN_ID);
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await screen.findByRole("button", { name: /registrar movimiento/i });
    expect(bodyOf(posts(f)[0]).orden_id).toBe(ORDEN_ID);
  });

  it("muestra el 409 de stock insuficiente", async () => {
    mockApi([...base, { method: "POST", path: "/api/v1/inventario/movimientos", status: 409, body: { detail: "FILT-05: stock 7, se piden 99" } }]);
    renderWithProviders(<InventarioPage />);
    await abrirMovimiento();
    await userEvent.selectOptions(screen.getByLabelText("Repuesto"), "FILT-05");
    await userEvent.selectOptions(screen.getByLabelText("Tipo de movimiento"), "AJUSTE_SALIDA");
    await userEvent.type(screen.getByLabelText("Cantidad"), "99");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("stock 7, se piden 99");
  });
});
