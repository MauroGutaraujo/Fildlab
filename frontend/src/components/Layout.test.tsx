import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import { Layout } from "./Layout";
import { renderWithProviders } from "../test/utils";

describe("Layout", () => {
  it("GERENCIA ve el enlace BI en el navbar", () => {
    renderWithProviders(<Layout />, { rol: "GERENCIA" });
    expect(screen.getByRole("link", { name: /bi/i })).toBeInTheDocument();
  });

  it("TECNICO no ve el enlace BI en el navbar", () => {
    renderWithProviders(<Layout />, { rol: "TECNICO" });
    expect(screen.queryByRole("link", { name: /bi/i })).not.toBeInTheDocument();
  });

  it("agrupa la navegación principal en una región administrativa", () => {
    renderWithProviders(<Layout />, { rol: "GERENCIA" });
    const aside = screen.getByRole("complementary", { name: "Navegación administrativa" });
    expect(within(aside).getByRole("navigation", { name: "Principal" })).toBeInTheDocument();
  });
});
