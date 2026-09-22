import { describe, expect, it, vi } from "vitest";
import { forwardRef } from "react";
import { render } from "@testing-library/react";
import { Firma } from "./Firma";

let propsRecibidas: Record<string, unknown> = {};

vi.mock("react-signature-canvas", () => ({
  default: forwardRef((props: Record<string, unknown>, _ref) => {
    propsRecibidas = props;
    return <canvas {...(props.canvasProps as object)} />;
  }),
}));

describe("Firma", () => {
  it("fija width y height explícitos en el canvas (sin esto, react-signature-canvas escala con el DPR del dispositivo y recorta el area dibujable)", () => {
    render(<Firma onCambio={() => {}} />);
    const canvasProps = propsRecibidas.canvasProps as Record<string, unknown>;
    expect(typeof canvasProps.width).toBe("number");
    expect(typeof canvasProps.height).toBe("number");
    expect(canvasProps.width as number).toBeGreaterThan(0);
    expect(canvasProps.height as number).toBeGreaterThan(0);
  });
});
