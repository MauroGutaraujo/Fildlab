import { describe, expect, it, vi } from "vitest";
import { guardarSesionTurno } from "../auth/session";
import { tokenDeTecnico } from "../test/token";
import { db, type OrdenLocal } from "./dexie";
import { exportarOrden, reintentarOrden } from "./recuperacion";

const ORDEN: OrdenLocal = {
  id: "33333333-3333-4333-8333-333333333333", tecnico_id: 1, contrato_id: 7, equipo_serie: "RO-1",
  tipo_intervencion: "CORRECTIVO", fecha_creacion_cliente: "2026-01-02T15:00:00Z",
  fecha_solicitud: "2026-01-02T12:00:00Z", fecha_primera_atencion: "2026-01-02T14:00:00Z",
  firma_base64: "original", gps_latitud: -8, gps_longitud: -79,
  lecturas_agua: { tds_entrada_ppm: 350, tds_post_membrana_ppm: 8, tds_producto_final_ppm: 5, ph: 7,
    conductividad_us_cm: 15, resistividad_mohm_cm: 1.2, litros_consumidos_red: 500, litros_agua_pura: 420 },
  repuestos_consumidos: [{ repuesto_codigo: "F-1", cantidad: 2 }], estado_sync: "error",
  error_status: 409, error_detalle: "Stock insuficiente", creado_en_local: "2026-01-02T11:00:00Z", intentos_sync: 3,
};

describe("recuperación local", () => {
  it("exporta todas las lecturas, firma, repuestos y tiempos SLA originales", async () => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add(ORDEN);
    expect(JSON.parse(await exportarOrden(ORDEN.id, 1))).toEqual(ORDEN);
  });

  it.each(["vencida", "renovacion"])("exporta localmente con sesión %s pero impide reintentar", async (estado) => {
    await guardarSesionTurno(tokenDeTecnico(1, estado === "vencida" ? 1 : undefined));
    if (estado === "renovacion") await db.sesion.update("actual", { requiere_renovacion: true });
    await db.ordenesLocal.add(ORDEN);
    expect(JSON.parse(await exportarOrden(ORDEN.id, 1))).toEqual(ORDEN);
    await expect(reintentarOrden(ORDEN.id, 1)).rejects.toThrow(/sesión/i);
    expect(await db.ordenesLocal.get(ORDEN.id)).toEqual(ORDEN);
  });

  it.each([null, "token-invalido"])("no exporta sin una sesión guardada estructuralmente válida (%s)", async (token) => {
    if (token) await guardarSesionTurno(token);
    await db.ordenesLocal.add(ORDEN);
    await expect(exportarOrden(ORDEN.id, 1)).rejects.toThrow(/sesión/i);
    expect(await db.ordenesLocal.get(ORDEN.id)).toEqual(ORDEN);
  });

  it("rechaza acceder directamente al UUID de otro propietario", async () => {
    await guardarSesionTurno(tokenDeTecnico(2));
    await db.ordenesLocal.add(ORDEN);
    await expect(exportarOrden(ORDEN.id, 2)).rejects.toThrow(/propietario/i);
    await expect(reintentarOrden(ORDEN.id, 2)).rejects.toThrow(/propietario/i);
    expect(await db.ordenesLocal.get(ORDEN.id)).toEqual(ORDEN);
  });

  it.each([422, undefined])("no reintenta un error %s aunque se invoque sin interfaz", async (status) => {
    await guardarSesionTurno(tokenDeTecnico());
    const bloqueada = { ...ORDEN, error_status: status };
    await db.ordenesLocal.add(bloqueada);
    const fetch = vi.spyOn(globalThis, "fetch");
    await expect(reintentarOrden(ORDEN.id, 1)).rejects.toThrow(/revisión/i);
    expect(await db.ordenesLocal.get(ORDEN.id)).toEqual(bloqueada);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("relee la sesión dentro de la transacción después de cargar la orden", async () => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add(ORDEN);
    const get = db.ordenesLocal.get.bind(db.ordenesLocal);
    const lectura = vi.spyOn(db.ordenesLocal, "get").mockImplementation((id) => get(id).then(async (orden) => {
      await db.sesion.put({ id: "actual", token: tokenDeTecnico(2), guardado_en: new Date().toISOString() });
      return orden;
    }));
    await expect(reintentarOrden(ORDEN.id, 1)).rejects.toThrow(/sesión/i);
    lectura.mockRestore();
    expect(await db.ordenesLocal.get(ORDEN.id)).toEqual(ORDEN);
  });

  it("el reintento exitoso sólo cambia seguimiento local, conserva el acta completa", async () => {
    await guardarSesionTurno(tokenDeTecnico());
    await db.ordenesLocal.add(ORDEN);
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ id: ORDEN.id }), { status: 201 }));
    await reintentarOrden(ORDEN.id, 1);
    const { estado_sync: _estado, error_status: _status, error_detalle: _error, creado_en_local: _creado, intentos_sync: _intentos, ...payload } = ORDEN;
    expect(JSON.parse(fetch.mock.calls[0][1]?.body as string)).toEqual(payload);
    expect(await db.ordenesLocal.get(ORDEN.id)).toEqual({ ...ORDEN, estado_sync: "sincronizada", error_detalle: undefined, error_status: undefined });
  });
});
