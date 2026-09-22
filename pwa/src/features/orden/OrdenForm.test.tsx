import { describe, expect, it, vi } from "vitest";
import { forwardRef, useImperativeHandle } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrdenForm } from "./OrdenForm";

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
  it("rechaza ph fuera de 0-14", async () => {
    render(<OrdenForm />);
    const ph = screen.getByLabelText(/^ph/i);
    await userEvent.type(ph, "15");
    await userEvent.tab();
    expect(await screen.findByText(/entre 0 y 14/i)).toBeInTheDocument();
  });

  it("rechaza un valor negativo en TDS entrada", async () => {
    render(<OrdenForm />);
    const campo = screen.getByLabelText(/tds.*entrada/i);
    await userEvent.type(campo, "-1");
    await userEvent.tab();
    expect(await screen.findByText(/no puede ser negativo/i)).toBeInTheDocument();
  });

  it("el boton de continuar sigue deshabilitado con lecturas incompletas", () => {
    render(<OrdenForm />);
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
    render(<OrdenForm />);
    await completarLecturasValidas();
    expect(screen.getByRole("button", { name: /cerrar orden/i })).toBeDisabled();
  });

  it("se habilita solo cuando lecturas + firma + gps estan completos", async () => {
    const getCurrentPosition = vi.fn((ok) => ok({ coords: { latitude: -8.11, longitude: -79.02 } }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    render(<OrdenForm />);
    await completarLecturasValidas();
    await userEvent.click(screen.getByRole("button", { name: /obtener ubicación/i }));
    await userEvent.click(screen.getByTestId("firma-canvas"));
    expect(await screen.findByRole("button", { name: /cerrar orden/i })).toBeEnabled();
  });
});
