import { useState } from "react";
import { db } from "../../db/dexie";
import { consumir } from "../../db/stock";
import { CAMPOS_LECTURA_ORDEN, type CampoLectura, errorLectura } from "../../lib/validators";
import { Firma } from "./Firma";
import { LecturasAguaFields } from "./LecturasAguaFields";
import { RepuestosSection } from "./RepuestosSection";
import { useGps } from "./useGps";

type Props = { contratoId: number; equipoSerie: string; tecnicoId: number; onCerrada?: () => void; onVolver?: () => void };

type Lecturas = Record<CampoLectura, string>;
const vacias = (): Lecturas =>
  Object.fromEntries(CAMPOS_LECTURA_ORDEN.map((c) => [c, ""])) as Lecturas;

export function OrdenForm({ contratoId, equipoSerie, tecnicoId, onCerrada, onVolver }: Props) {
  const [lecturas, setLecturas] = useState<Lecturas>(vacias());
  const [tocado, setTocado] = useState<Partial<Record<CampoLectura, boolean>>>({});
  const [firma, setFirma] = useState<string | null>(null);
  const [tipoIntervencion, setTipoIntervencion] = useState<"PREVENTIVO" | "CORRECTIVO">("PREVENTIVO");
  const [errorGuardado, setErrorGuardado] = useState<string | null>(null);
  const [repuestos, setRepuestos] = useState<{ repuesto_codigo: string; cantidad: number }[]>([]);
  const [codigoRepuesto, setCodigoRepuesto] = useState("");
  const [cantidadRepuesto, setCantidadRepuesto] = useState("");
  const [errorRepuesto, setErrorRepuesto] = useState<string | null>(null);
  const gps = useGps();

  const errores = Object.fromEntries(
    CAMPOS_LECTURA_ORDEN.map((c) => [c, errorLectura(c, lecturas[c])]),
  ) as Record<CampoLectura, string | null>;
  const lecturasCompletas = CAMPOS_LECTURA_ORDEN.every((c) => errores[c] === null);
  const gpsCompleto = gps.lat !== null && gps.lng !== null;
  const puedeCerrar = lecturasCompletas && firma !== null && gpsCompleto;

  async function agregarRepuesto() {
    const codigo = codigoRepuesto.trim();
    const cantidad = Number(cantidadRepuesto);
    if (!codigo || !Number.isInteger(cantidad) || cantidad <= 0) {
      setErrorRepuesto("Indica un código y una cantidad válida");
      return;
    }
    // Descuenta del stock móvil local de inmediato (RN-03 fase 1, REQ-06): si no alcanza,
    // consumir() rechaza sin tocar el registro.
    const r = await consumir(codigo, cantidad);
    if (!r.ok) {
      setErrorRepuesto(r.motivo);
      return;
    }
    setErrorRepuesto(null);
    setRepuestos((prev) => [...prev, { repuesto_codigo: codigo, cantidad }]);
    setCodigoRepuesto("");
    setCantidadRepuesto("");
  }

  async function cerrarOrden() {
    if (!puedeCerrar || firma === null || gps.lat === null || gps.lng === null) return;
    setErrorGuardado(null);
    const ahora = new Date().toISOString();
    try {
      await db.ordenesLocal.add({
        id: crypto.randomUUID(),
        contrato_id: contratoId,
        equipo_serie: equipoSerie,
        tecnico_id: tecnicoId,
        tipo_intervencion: tipoIntervencion,
        fecha_creacion_cliente: ahora,
        lecturas_agua: Object.fromEntries(CAMPOS_LECTURA_ORDEN.map((c) => [c, Number(lecturas[c])])) as never,
        firma_base64: firma,
        gps_latitud: gps.lat,
        gps_longitud: gps.lng,
        repuestos_consumidos: repuestos,
        estado_sync: "pendiente",
        creado_en_local: ahora,
        intentos_sync: 0,
      });
    } catch {
      // Cuota de IndexedDB excedida, modo privado, etc.: el técnico debe enterarse, no perder
      // el acta en silencio (RNF-04). Las lecturas/firma/GPS quedan intactos para reintentar.
      setErrorGuardado("No se pudo guardar la orden en este dispositivo. Verifica el espacio disponible e intenta de nuevo.");
      return;
    }
    onCerrada?.();
  }

  return (
    <section className="space-y-4 p-4 pb-32">
      <div className="flex items-center justify-between gap-3 rounded-xl border border-blue-100 bg-white p-4 shadow-sm">
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Orden de servicio</span>
          <p className="mt-1 text-base font-bold text-slate-950">Equipo: {equipoSerie}</p>
        </div>
        {onVolver && (
          <button
            type="button"
            onClick={onVolver}
            className="min-h-10 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            ← Volver a equipos
          </button>
        )}
      </div>
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-950">Lecturas de agua</h1>
        <p className="mt-1 text-sm text-slate-600">Registra los valores medidos del sistema.</p>
      </div>
      <LecturasAguaFields
        lecturas={lecturas}
        tocado={tocado}
        errores={errores}
        onValor={(campo, valor) => setLecturas((prev) => ({ ...prev, [campo]: valor }))}
        onTocado={(campo) => setTocado((prev) => ({ ...prev, [campo]: true }))}
      />
      <button type="button" disabled={!lecturasCompletas} className="min-h-12 w-full rounded-lg bg-blue-700 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60">
        Continuar
      </button>

      {lecturasCompletas && (
        <div className="space-y-4">
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-base font-bold text-slate-900">Tipo de intervención</h2>
            <select
              value={tipoIntervencion}
              onChange={(e) => setTipoIntervencion(e.target.value as "PREVENTIVO" | "CORRECTIVO")}
              className="min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-3 text-base text-slate-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            >
              <option value="PREVENTIVO">Preventivo</option>
              <option value="CORRECTIVO">Correctivo</option>
            </select>
          </section>
          <RepuestosSection
            codigo={codigoRepuesto}
            cantidad={cantidadRepuesto}
            repuestos={repuestos}
            error={errorRepuesto}
            onCodigoChange={setCodigoRepuesto}
            onCantidadChange={setCantidadRepuesto}
            onAgregar={agregarRepuesto}
          />
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-base font-bold text-slate-900">Firma del técnico</h2>
            <Firma onCambio={setFirma} />
          </section>
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-base font-bold text-slate-900">Ubicación del servicio</h2>
            <button type="button" onClick={gps.solicitar} className="min-h-12 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-900 transition hover:bg-blue-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
              Obtener ubicación
            </button>
            {gps.error && <p role="alert" className="mt-2 text-sm font-medium text-rose-700">{gps.error}</p>}
            {gpsCompleto && (
              <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
                {gps.lat}, {gps.lng}
              </p>
            )}
          </section>
          {errorGuardado && (
            <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-medium text-rose-800">
              {errorGuardado}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              type="button"
              disabled={!puedeCerrar}
              onClick={cerrarOrden}
              className="min-h-12 flex-1 rounded-lg bg-emerald-700 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cerrar orden
            </button>
            {onVolver && (
              <button
                type="button"
                onClick={onVolver}
                className="min-h-12 rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                Cancelar y volver
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
