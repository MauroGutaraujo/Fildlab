import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MisOrdenes } from "./MisOrdenes";
import { db } from "../../db/dexie";

const ORDEN_BASE = {
  contrato_id: 1, equipo_serie: "RO-1", tecnico_id: 1, tipo_intervencion: "PREVENTIVO",
  fecha_creacion_cliente: "2026-03-01T10:00:00Z",
  lecturas_agua: { tds_entrada_ppm: 1, tds_post_membrana_ppm: 1, tds_producto_final_ppm: 1, ph: 7,
                   conductividad_us_cm: 1, resistividad_mohm_cm: 1, litros_consumidos_red: 1, litros_agua_pura: 1 },
  firma_base64: "AAAA", gps_latitud: -8, gps_longitud: -79, repuestos_consumidos: [], intentos_sync: 0,
};

function conProvider(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("MisOrdenes", () => {
  it("muestra 'sin ordenes' cuando no hay ninguna", async () => {
    conProvider(<MisOrdenes />);
    expect(await screen.findByText(/no hay órdenes/i)).toBeInTheDocument();
  });

  it("lista las ordenes con su estado y el detalle del error si lo tiene", async () => {
    await db.ordenesLocal.bulkAdd([
      { ...ORDEN_BASE, id: "11111111-1111-1111-1111-111111111111", estado_sync: "pendiente", creado_en_local: "2026-03-01T10:00:00Z" },
      { ...ORDEN_BASE, id: "22222222-2222-2222-2222-222222222222", estado_sync: "error",
        error_detalle: "FILT-05: stock 2, se piden 5", creado_en_local: "2026-03-01T10:01:00Z" },
    ]);
    conProvider(<MisOrdenes />);
    expect(await screen.findByText(/pendiente/i)).toBeInTheDocument();
    expect(await screen.findByText(/error/i)).toBeInTheDocument();
    expect(await screen.findByText(/stock 2, se piden 5/i)).toBeInTheDocument();
  });
});
