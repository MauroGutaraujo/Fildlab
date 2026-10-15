import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataTable } from "./DataTable";

type Fila = { id: number; nombre: string };
const columns = [{ header: "Nombre", cell: (f: Fila) => f.nombre }];

describe("DataTable", () => {
  it("muestra el estado vacío", () => {
    render(<DataTable columns={columns} rows={[]} rowKey={(f) => f.id} />);
    expect(screen.getByText("Sin datos disponibles")).toBeInTheDocument();
  });

  it("renderiza encabezados y filas", () => {
    render(<DataTable columns={columns} rows={[{ id: 1, nombre: "Ana" }, { id: 2, nombre: "Luis" }]} rowKey={(f) => f.id} />);
    expect(screen.getByRole("columnheader", { name: "Nombre" })).toBeInTheDocument();
    expect(screen.getByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("Luis")).toBeInTheDocument();
  });

  it("mantiene una envoltura de desplazamiento para tablas anchas", () => {
    render(<DataTable columns={columns} rows={[{ id: 1, nombre: "Ana" }]} rowKey={(f) => f.id} />);
    expect(screen.getByRole("table").parentElement).toHaveClass("overflow-x-auto");
  });

  it("sin onEdit no hay acciones de edición", () => {
    render(<DataTable columns={columns} rows={[{ id: 1, nombre: "Ana" }]} rowKey={(f) => f.id} />);
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
  });

  it("con onEdit muestra el botón y lo invoca con la fila", async () => {
    const onEdit = vi.fn();
    render(<DataTable columns={columns} rows={[{ id: 1, nombre: "Ana" }]} rowKey={(f) => f.id} onEdit={onEdit} />);
    await userEvent.click(screen.getByRole("button", { name: /editar/i }));
    expect(onEdit).toHaveBeenCalledWith({ id: 1, nombre: "Ana" });
  });

  it("canEdit oculta «Editar» solo en las filas que no son editables", () => {
    render(
      <DataTable
        columns={columns}
        rows={[{ id: 1, nombre: "Ana" }, { id: 2, nombre: "Luis" }]}
        rowKey={(f) => f.id}
        onEdit={() => {}}
        canEdit={(f) => f.id === 2}
      />,
    );
    expect(screen.getAllByRole("button", { name: /editar/i })).toHaveLength(1);
  });

  it("renderiza acciones personalizadas por fila", () => {
    render(
      <DataTable
        columns={columns}
        rows={[{ id: 1, nombre: "Ana" }]}
        rowKey={(f) => f.id}
        actions={(f) => <button>Anular {f.nombre}</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Anular Ana" })).toBeInTheDocument();
  });

  it("muestra «Cargando…» mientras carga", () => {
    render(<DataTable columns={columns} rows={[]} rowKey={(f) => f.id} loading />);
    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
    expect(screen.queryByText("Sin datos disponibles")).not.toBeInTheDocument();
  });

  it("muestra el error si falla la carga", () => {
    render(<DataTable columns={columns} rows={[]} rowKey={(f) => f.id} error="No se pudo cargar" />);
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo cargar");
  });
});
