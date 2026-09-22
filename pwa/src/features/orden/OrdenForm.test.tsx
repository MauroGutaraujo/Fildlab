import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrdenForm } from "./OrdenForm";

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
});
