import { useState } from "react";
import { db } from "../../db/dexie";
import { consumir } from "../../db/stock";
import { CAMPOS_LECTURA_ORDEN, type CampoLectura, errorLectura } from "../../lib/validators";
import { Firma } from "./Firma";
import { useGps } from "./useGps";

type Props = { contratoId: number; equipoSerie: string; tecnicoId: number; onCerrada?: () => void };

const ETIQUETAS: Record<CampoLectura, string> = {
  tds_entrada_ppm: "TDS entrada (ppm)",
  tds_post_membrana_ppm: "TDS post-membrana (ppm)",
  tds_producto_final_ppm: "TDS producto final (ppm)",
  ph: "pH",
  conductividad_us_cm: "Conductividad (µS/cm)",
  resistividad_mohm_cm: "Resistividad (MΩ·cm)",
  litros_consumidos_red: "Litros consumidos de red",
  litros_agua_pura: "Litros de agua pura",
};

type Lecturas = Record<CampoLectura, string>;
const vacias = (): Lecturas =>
  Object.fromEntries(CAMPOS_LECTURA_ORDEN.map((c) => [c, ""])) as Lecturas;

export function OrdenForm({ contratoId, equipoSerie, tecnicoId, onCerrada }: Props) {
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
    <section className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Lecturas de agua</h1>
      <div className="grid gap-3 sm:grid-cols-2">
        {CAMPOS_LECTURA_ORDEN.map((campo) => (
          <label key={campo} className="block text-sm">
            {ETIQUETAS[campo]}
            <input
              id={campo}
              value={lecturas[campo]}
              onChange={(e) => setLecturas((prev) => ({ ...prev, [campo]: e.target.value }))}
              onBlur={() => setTocado((prev) => ({ ...prev, [campo]: true }))}
              inputMode="decimal"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
            {tocado[campo] && errores[campo] && <p className="mt-1 text-red-700">{errores[campo]}</p>}
          </label>
        ))}
      </div>
      <button type="button" disabled={!lecturasCompletas} className="mt-4 rounded bg-sky-700 px-4 py-2 text-white disabled:opacity-60">
        Continuar
      </button>

      {lecturasCompletas && (
        <div className="mt-6 space-y-4">
          <div>
            <h2 className="mb-1 font-medium">Tipo de intervención</h2>
            <select
              value={tipoIntervencion}
              onChange={(e) => setTipoIntervencion(e.target.value as "PREVENTIVO" | "CORRECTIVO")}
              className="rounded border border-slate-300 px-3 py-2"
            >
              <option value="PREVENTIVO">Preventivo</option>
              <option value="CORRECTIVO">Correctivo</option>
            </select>
          </div>
          <div>
            <h2 className="mb-1 font-medium">Repuestos consumidos</h2>
            <div className="flex flex-wrap items-end gap-2">
              <label className="text-sm">
                Código de repuesto
                <input
                  value={codigoRepuesto}
                  onChange={(e) => setCodigoRepuesto(e.target.value)}
                  className="mt-1 block rounded border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="text-sm">
                Cantidad consumida
                <input
                  value={cantidadRepuesto}
                  onChange={(e) => setCantidadRepuesto(e.target.value)}
                  inputMode="numeric"
                  className="mt-1 block rounded border border-slate-300 px-3 py-2"
                />
              </label>
              <button type="button" onClick={agregarRepuesto} className="rounded border border-sky-700 px-4 py-2 text-sky-700">
                Agregar repuesto
              </button>
            </div>
            {errorRepuesto && <p className="mt-1 text-red-700">{errorRepuesto}</p>}
            {repuestos.length > 0 && (
              <ul className="mt-2 text-sm text-slate-600">
                {repuestos.map((r, i) => (
                  <li key={i}>
                    {r.repuesto_codigo} × {r.cantidad}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h2 className="mb-1 font-medium">Firma</h2>
            <Firma onCambio={setFirma} />
          </div>
          <div>
            <h2 className="mb-1 font-medium">Ubicación</h2>
            <button type="button" onClick={gps.solicitar} className="rounded border border-sky-700 px-4 py-2 text-sky-700">
              Obtener ubicación
            </button>
            {gps.error && <p className="mt-1 text-red-700">{gps.error}</p>}
            {gpsCompleto && (
              <p className="mt-1 text-sm text-slate-600">
                {gps.lat}, {gps.lng}
              </p>
            )}
          </div>
          {errorGuardado && (
            <p role="alert" className="text-red-700">
              {errorGuardado}
            </p>
          )}
          <button
            type="button"
            disabled={!puedeCerrar}
            onClick={cerrarOrden}
            className="rounded bg-emerald-700 px-4 py-2 text-white disabled:opacity-60"
          >
            Cerrar orden
          </button>
        </div>
      )}
    </section>
  );
}
