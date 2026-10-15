import { describe, expect, it, vi } from "vitest";
import { forwardRef, useImperativeHandle } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrdenForm } from "./OrdenForm";
import { db } from "../../db/dexie";
import { cargarStockTurno } from "../../db/stock";

// react-signature-canvas usa signature_pad, que necesita un CanvasRenderingContext2D real
// (jsdom no lo implementa). Se reemplaza por un doble mínimo que expone el mismo contrato
// de ref (isEmpty/toDataURL/clear) y dispara onEnd con un click, sin dibujar de verdad —
// lo que se prueba aquí es la integración con OrdenForm, no signature_pad.
vi.mock("react-signature-canvas", () => ({
  default: forwardRef((props: { canvasProps?: Record<string, unknown>; onEnd?: () => void }, ref) => {
    useImperativeHandle(ref, () => ({ isEmpty: () => false, toDataURL: () => "data:image/png;base64,FIRMA", clear: () => {} }));
    return <canvas {...props.canvasProps} onClick={props.onEnd} />;
  }),
}));

describe("OrdenForm — lecturas de agua", () => {
  it("agrupa las lecturas de calidad y volumen con etiquetas accesibles", () => {
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    const calidad = screen.getByRole("group", { name: "Calidad del agua" });
    const volumen = screen.getByRole("group", { name: "Producción y consumo" });

    expect(within(calidad).getByLabelText(/tds entrada/i)).toBeInTheDocument();
    expect(within(calidad).getByLabelText(/^ph$/i)).toBeInTheDocument();
    expect(within(calidad).getByLabelText(/conductividad/i)).toBeInTheDocument();
    expect(within(volumen).getByLabelText(/litros consumidos/i)).toBeInTheDocument();
    expect(within(volumen).getByLabelText(/litros de agua pura/i)).toBeInTheDocument();
  });

  it("rechaza ph fuera de 0-14", async () => {
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    const ph = screen.getByLabelText(/^ph/i);
    await userEvent.type(ph, "15");
    await userEvent.tab();
    expect(await screen.findByText(/entre 0 y 14/i)).toBeInTheDocument();
  });

  it("rechaza un valor negativo en TDS entrada", async () => {
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    const campo = screen.getByLabelText(/tds.*entrada/i);
    await userEvent.type(campo, "-1");
    await userEvent.tab();
    expect(await screen.findByText(/no puede ser negativo/i)).toBeInTheDocument();
  });

  it("rechaza una lectura no numérica", async () => {
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    const campo = screen.getByLabelText(/tds.*entrada/i);
    await userEvent.type(campo, "abc");
    await userEvent.tab();
    expect(await screen.findByText(/debe ser un número/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continuar/i })).toBeDisabled();
  });

  it("el boton de continuar sigue deshabilitado con lecturas incompletas", () => {
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    expect(screen.getByRole("button", { name: /continuar/i })).toBeDisabled();
  });

  async function completarLecturasValidas() {
    const valores: Record<string, string> = {
      "tds-entrada-ppm": "350", "tds-post-membrana-ppm": "8", "tds-producto-final-ppm": "5",
      ph: "7", "conductividad-us-cm": "15", "resistividad-mohm-cm": "1.2",
      "litros-consumidos-red": "500", "litros-agua-pura": "420",
    };
    for (const [id, valor] of Object.entries(valores)) {
      await userEvent.type(document.getElementById(id.replace(/-/g, "_")) as HTMLElement, valor);
    }
  }

  it("cerrar orden sigue deshabilitado sin firma ni GPS aun con lecturas completas", async () => {
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    await completarLecturasValidas();
    expect(screen.getByRole("button", { name: /cerrar orden/i })).toBeDisabled();
  });

  it("se habilita solo cuando lecturas + firma + gps estan completos", async () => {
    const getCurrentPosition = vi.fn((ok) => ok({ coords: { latitude: -8.11, longitude: -79.02 } }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    await completarLecturasValidas();
    await userEvent.click(screen.getByRole("button", { name: /obtener ubicación/i }));
    await userEvent.click(screen.getByTestId("firma-canvas"));
    expect(await screen.findByRole("button", { name: /cerrar orden/i })).toBeEnabled();
  });

  it("borrar la firma después de completar lecturas y GPS vuelve a bloquear el cierre", async () => {
    const getCurrentPosition = vi.fn((ok) => ok({ coords: { latitude: -8.11, longitude: -79.02 } }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    await completarLecturasValidas();
    await userEvent.click(screen.getByRole("button", { name: /obtener ubicación/i }));
    await userEvent.click(screen.getByTestId("firma-canvas"));
    expect(await screen.findByRole("button", { name: /cerrar orden/i })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: /limpiar firma/i }));
    expect(screen.getByRole("button", { name: /cerrar orden/i })).toBeDisabled();
  });

  it("si falla la escritura en Dexie al cerrar (ej. cuota excedida), se avisa y no navega", async () => {
    const getCurrentPosition = vi.fn((ok) => ok({ coords: { latitude: -8.11, longitude: -79.02 } }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    vi.spyOn(db.ordenesLocal, "add").mockRejectedValueOnce(new Error("QuotaExceededError"));
    const onCerrada = vi.fn();
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} onCerrada={onCerrada} />);
    await completarLecturasValidas();
    await userEvent.click(screen.getByRole("button", { name: /obtener ubicación/i }));
    await userEvent.click(screen.getByTestId("firma-canvas"));
    await userEvent.click(await screen.findByRole("button", { name: /cerrar orden/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo guardar/i);
    expect(onCerrada).not.toHaveBeenCalled();
  });

  it("al cerrar, escribe la orden en ordenesLocal con estado_sync pendiente", async () => {
    const getCurrentPosition = vi.fn((ok) => ok({ coords: { latitude: -8.11, longitude: -79.02 } }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    await completarLecturasValidas();
    await userEvent.click(screen.getByRole("button", { name: /obtener ubicación/i }));
    await userEvent.click(screen.getByTestId("firma-canvas"));
    await userEvent.click(await screen.findByRole("button", { name: /cerrar orden/i }));
    const guardadas = await db.ordenesLocal.toArray();
    expect(guardadas).toHaveLength(1);
    expect(guardadas[0]).toMatchObject({
      contrato_id: 1, equipo_serie: "RO-1", tecnico_id: 2, estado_sync: "pendiente",
      firma_base64: "data:image/png;base64,FIRMA", gps_latitud: -8.11, gps_longitud: -79.02,
    });
    expect(guardadas[0].lecturas_agua.tds_entrada_ppm).toBe(350);
    expect(guardadas[0].repuestos_consumidos).toEqual([]);
  });

  it("agregar un repuesto consumido lo descuenta del stock movil local y lo incluye al cerrar", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 10 }], "turno-test");
    const getCurrentPosition = vi.fn((ok) => ok({ coords: { latitude: -8.11, longitude: -79.02 } }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    await completarLecturasValidas();
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/cantidad consumida/i), "3");
    await userEvent.click(screen.getByRole("button", { name: /agregar repuesto/i }));
    expect(await screen.findByText(/FILT-05.*3/)).toBeInTheDocument();
    expect((await db.stockMovilLocal.get("FILT-05"))?.cantidad_consumida).toBe(3);

    await userEvent.click(screen.getByRole("button", { name: /obtener ubicación/i }));
    await userEvent.click(screen.getByTestId("firma-canvas"));
    await userEvent.click(await screen.findByRole("button", { name: /cerrar orden/i }));
    const guardada = (await db.ordenesLocal.toArray())[0];
    expect(guardada.repuestos_consumidos).toEqual([{ repuesto_codigo: "FILT-05", cantidad: 3 }]);
  });

  it("agregar un repuesto que excede el stock movil local se rechaza y no se agrega", async () => {
    await cargarStockTurno([{ repuesto_codigo: "FILT-05", cantidad: 2 }], "turno-test");
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    await completarLecturasValidas();
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/cantidad consumida/i), "5");
    await userEvent.click(screen.getByRole("button", { name: /agregar repuesto/i }));
    expect(await screen.findByText(/stock móvil insuficiente/i)).toBeInTheDocument();
    expect(screen.queryByText(/FILT-05.*5/)).not.toBeInTheDocument();
  });

  it("rechaza una cantidad de repuesto inválida sin agregarla", async () => {
    render(<OrdenForm contratoId={1} equipoSerie="RO-1" tecnicoId={2} />);
    await completarLecturasValidas();
    await userEvent.type(screen.getByLabelText(/código de repuesto/i), "FILT-05");
    await userEvent.type(screen.getByLabelText(/cantidad consumida/i), "0");
    await userEvent.click(screen.getByRole("button", { name: /agregar repuesto/i }));
    expect(await screen.findByText(/cantidad válida/i)).toBeInTheDocument();
    expect(screen.queryByText(/FILT-05.*0/)).not.toBeInTheDocument();
  });
});
