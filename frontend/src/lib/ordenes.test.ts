import { describe, expect, it } from "vitest";
import { formatearOrdenAmigable, razonSocialDeOrden } from "./ordenes";

const ORDEN = { id: "2ccc7daf-0000-0000-0000-000000000000", contrato_id: 1, fecha_creacion_cliente: "2026-10-15T10:00:00Z" };
const CONTRATOS = [{ id: 1, cliente_ruc: "20612493821" }];
const CLIENTES = [{ ruc: "20612493821", razon_social: "CLINICA SANCHEZ FERRER" }];

describe("formatearOrdenAmigable", () => {
  it("usa el correlativo, las siglas del cliente y la fecha DDMMAA", () => {
    const razon = razonSocialDeOrden(ORDEN.contrato_id, CONTRATOS, CLIENTES);
    expect(razon).toBe("CLINICA SANCHEZ FERRER");
    expect(formatearOrdenAmigable(ORDEN, razon, 0)).toBe("OT-01CSF151026");
  });

  it("sin cliente vinculado usa GEN", () => {
    expect(formatearOrdenAmigable(ORDEN, null, 0)).toBe("OT-01GEN151026");
  });

  it("sin índice usa los dos primeros caracteres hex del UUID en mayúscula", () => {
    expect(formatearOrdenAmigable(ORDEN, "CLINICA SANCHEZ FERRER")).toBe("OT-2CCSF151026");
  });

  it("razonSocialDeOrden devuelve null si el contrato no existe", () => {
    expect(razonSocialDeOrden(999, CONTRATOS, CLIENTES)).toBeNull();
  });

  it("siglas con dos palabras (ej. Hospital Regional)", () => {
    const razon = razonSocialDeOrden(1, CONTRATOS, [{ ruc: "20612493821", razon_social: "HOSPITAL REGIONAL" }]);
    expect(formatearOrdenAmigable(ORDEN, razon, 0)).toBe("OT-01HR151026");
  });
});
