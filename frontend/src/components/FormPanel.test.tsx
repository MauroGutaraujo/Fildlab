import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { FormPanel } from "./FormPanel";

describe("FormPanel", () => {
  it("se desplaza a la vista al abrirse, para que sea visible aunque la página esté scrolleada", () => {
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    render(
      <FormPanel title="Editar contrato" onSubmit={() => {}} onCancel={() => {}}>
        <div>contenido</div>
      </FormPanel>,
    );

    expect(scrollIntoView).toHaveBeenCalled();
  });
});
