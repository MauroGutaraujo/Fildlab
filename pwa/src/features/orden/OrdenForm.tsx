import { useEffect, useState } from "react";
import { db, type StockTecnicoItem } from "../../db/dexie";
import { obtenerRepuestosCatalogo, type RepuestoApi } from "../../db/catalogo";
import { cerrarBorrador, descartarBorrador } from "../../db/ordenes";
import { comprobarDisponibilidad } from "../../db/stock";
import { CAMPOS_LECTURA_ORDEN, type CampoLectura, errorLectura } from "../../lib/validators";
import { Firma } from "./Firma";
import { LecturasAguaFields } from "./LecturasAguaFields";
import { RepuestosSection } from "./RepuestosSection";
import { useGps } from "./useGps";
import { useBorradorOrden } from "./useBorradorOrden";
import { errorTiemposServicio } from "../../lib/tiemposServicio";

type Props = { contratoId: number; equipoSerie: string; tecnicoId: number; onCerrada?: () => void; onVolver?: () => void };

export function OrdenForm({ contratoId, equipoSerie, tecnicoId, onCerrada, onVolver }: Props) {
  const draft = useBorradorOrden(tecnicoId, equipoSerie, contratoId);
  const [tocado, setTocado] = useState<Partial<Record<CampoLectura, boolean>>>({});
  const [errorGuardado, setErrorGuardado] = useState<string | null>(null);
  const [codigoRepuesto, setCodigoRepuesto] = useState("");
  const [cantidadRepuesto, setCantidadRepuesto] = useState("");
  const [errorRepuesto, setErrorRepuesto] = useState<string | null>(null);
  const [cerrando, setCerrando] = useState(false);
  const [agregando, setAgregando] = useState(false);
  const [firmaEnEdicion, setFirmaEnEdicion] = useState(false);
  const gps = useGps();
  const { cambiar } = draft;
  const [stockTecnico, setStockTecnico] = useState<StockTecnicoItem[]>([]);
  const [catalogo, setCatalogo] = useState<RepuestoApi[]>([]);

  useEffect(() => {
    if (gps.lat !== null && gps.lng !== null) cambiar({ gps_latitud: gps.lat, gps_longitud: gps.lng });
  }, [gps.lat, gps.lng, cambiar]);

  useEffect(() => {
    let activo = true;
    db.stockPorTecnico.where("tecnico_id").equals(tecnicoId).toArray()
      .then((items) => { if (activo) setStockTecnico(items); })
      .catch(() => {});
    obtenerRepuestosCatalogo().then((items) => { if (activo) setCatalogo(items); }).catch(() => {});
    return () => { activo = false; };
  }, [tecnicoId]);

  if (!draft.borrador) return <section className="p-4"><p role={draft.error ? "alert" : "status"}>{draft.error ?? "Recuperando borrador…"}</p></section>;
  const { lecturas, firma_base64: firma, tipo_intervencion: tipoIntervencion, repuestos_consumidos: repuestos,
    gps_latitud: lat, gps_longitud: lng } = draft.borrador;
  const sugerenciasStock = stockTecnico
    .map((item) => {
      const enEstaOrden = repuestos.filter((r) => r.repuesto_codigo === item.repuesto_codigo).reduce((total, r) => total + r.cantidad, 0);
      return { codigo: item.repuesto_codigo, disponible: item.cantidad_cargada - item.cantidad_consumida - enEstaOrden };
    })
    .filter((s) => s.disponible > 0)
    .map((s) => ({ codigo: s.codigo, texto: `${s.codigo} — ${s.disponible} disponibles` }));
  // Sin stock cargado todavía, el catálogo general sirve como referencia de códigos válidos;
  // intentar consumir uno sin stock sigue siendo rechazado por comprobarDisponibilidad.
  const sugerenciasRepuestos = sugerenciasStock.length > 0 ? sugerenciasStock
    : catalogo.map((r) => ({ codigo: r.codigo, texto: `${r.codigo} — ${r.descripcion}` }));
  const errores = Object.fromEntries(CAMPOS_LECTURA_ORDEN.map((c) => [c, errorLectura(c, lecturas[c])])) as Record<CampoLectura, string | null>;
  const lecturasCompletas = CAMPOS_LECTURA_ORDEN.every((c) => errores[c] === null);
  const gpsCompleto = lat !== null && lng !== null;
  const errorTiempos = errorTiemposServicio(draft.borrador.fecha_solicitud, draft.borrador.fecha_primera_atencion);
  const puedeCerrar = lecturasCompletas && firma !== null && gpsCompleto && !cerrando && !agregando && !draft.error && !errorTiempos;

  async function agregarRepuesto() {
    const codigo = codigoRepuesto.trim();
    const cantidad = Number(cantidadRepuesto);
    if (!codigo || !Number.isSafeInteger(cantidad) || cantidad <= 0) {
      setErrorRepuesto("Indica un código y una cantidad válida"); return;
    }
    if (agregando || cerrando) return;
    draft.bloqueado.current = true;
    setAgregando(true);
    try {
      const seleccionada = repuestos.filter((r) => r.repuesto_codigo === codigo).reduce((total, r) => total + r.cantidad, 0);
      await comprobarDisponibilidad(codigo, seleccionada + cantidad, tecnicoId);
      draft.bloqueado.current = false;
      cambiar({ repuestos_consumidos: [...repuestos, { repuesto_codigo: codigo, cantidad }] });
      setErrorRepuesto(null); setCodigoRepuesto(""); setCantidadRepuesto("");
    } catch (e) {
      setErrorRepuesto(e instanceof Error ? e.message : "No se pudo verificar el stock móvil");
    } finally { draft.bloqueado.current = false; setAgregando(false); }
  }

  async function cerrarOrden() {
    if (!puedeCerrar || draft.bloqueado.current) return;
    draft.bloqueado.current = true;
    setCerrando(true); setErrorGuardado(null);
    try {
      const b = await draft.esperar();
      await cerrarBorrador(b);
      draft.permitirSalida();
      onCerrada?.();
    } catch (e) {
      draft.bloqueado.current = false;
      setErrorGuardado(`No se pudo guardar la orden. ${e instanceof Error ? e.message : "Verifica el espacio disponible e intenta de nuevo."}`);
    } finally { setCerrando(false); }
  }

  async function descartar() {
    if (draft.bloqueado.current) return;
    draft.bloqueado.current = true;
    setCerrando(true);
    try {
      await draft.esperar().catch(() => {});
      const b = draft.obtenerActual();
      if (!b) throw new Error("El borrador no está disponible");
      await descartarBorrador(b);
      draft.permitirSalida();
      onVolver?.();
    } catch (e) {
      draft.bloqueado.current = false;
      setErrorGuardado(`No se pudo descartar el borrador. ${e instanceof Error ? e.message : "Intenta de nuevo."}`);
    } finally { setCerrando(false); }
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
            onClick={() => { if (window.dispatchEvent(new CustomEvent("fildlab:antes-navegar", { cancelable: true }))) onVolver?.(); }}
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
      <p role="status" className="text-sm text-slate-600">{draft.guardando ? "Guardando borrador…" : draft.error ? "Hay cambios sin guardar" : "Borrador guardado en este dispositivo"}</p>
      {draft.error && <div role="alert" className="text-rose-700"><p>{draft.error}</p>{draft.conflicto
        ? <button type="button" disabled={draft.guardando} onClick={async () => { await draft.recuperar(); setFirmaEnEdicion(false); }}>Descartar cambios locales y recuperar versión guardada</button>
        : <button type="button" onClick={draft.reintentar}>Reintentar guardado</button>}</div>}
      {errorGuardado && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-medium text-rose-800">{errorGuardado}</p>}
      <fieldset disabled={cerrando || agregando || draft.conflicto} className="space-y-4">
      <section className="space-y-2 rounded-xl border bg-white p-4">
        <h2 className="font-bold">Tiempos de atención (opcional)</h2>
        <p className="text-sm text-slate-600">Registra las fechas reales para medir el tiempo de respuesta. Usa la hora de este dispositivo; deja ambas vacías si no las conoces.</p>
        <label className="block">Solicitud del servicio<input aria-label="Solicitud del servicio" type="datetime-local" value={draft.borrador.fecha_solicitud ?? ""} onChange={(e) => cambiar({ fecha_solicitud: e.target.value })} className="block min-h-12 w-full rounded border p-2" /></label>
        <label className="block">Primera atención<input aria-label="Primera atención" type="datetime-local" value={draft.borrador.fecha_primera_atencion ?? ""} onChange={(e) => cambiar({ fecha_primera_atencion: e.target.value })} className="block min-h-12 w-full rounded border p-2" /></label>
        {errorTiempos && <p className="text-sm text-rose-700">{errorTiempos}</p>}
      </section>
      <LecturasAguaFields
        lecturas={lecturas}
        tocado={tocado}
        errores={errores}
        onValor={(campo, valor) => cambiar({ lecturas: { ...lecturas, [campo]: valor } })}
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
              onChange={(e) => cambiar({ tipo_intervencion: e.target.value as "PREVENTIVO" | "CORRECTIVO" })}
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
            sugerencias={sugerenciasRepuestos}
            onCodigoChange={setCodigoRepuesto}
            onCantidadChange={setCantidadRepuesto}
            onAgregar={agregarRepuesto}
          />
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-base font-bold text-slate-900">Firma del cliente</h2>
            {firma && !firmaEnEdicion ? <div className="space-y-2"><img src={firma} alt="Firma guardada" className="w-full rounded border bg-white" /><button type="button" onClick={() => { setFirmaEnEdicion(true); cambiar({ firma_base64: null }); }} className="min-h-11 rounded border px-4">Limpiar firma</button></div>
              : <Firma onCambio={(valor) => { setFirmaEnEdicion(true); cambiar({ firma_base64: valor }); }} />}
          </section>
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-base font-bold text-slate-900">Ubicación del servicio</h2>
            <button type="button" onClick={gps.solicitar} className="min-h-12 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-900 transition hover:bg-blue-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
              Obtener ubicación
            </button>
            {gps.error && <p role="alert" className="mt-2 text-sm font-medium text-rose-700">{gps.error}</p>}
            {gpsCompleto && (
              <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
                {lat}, {lng}
              </p>
            )}
          </section>
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
                onClick={() => { if (window.dispatchEvent(new CustomEvent("fildlab:antes-navegar", { cancelable: true }))) onVolver?.(); }}
                className="min-h-12 rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                Guardar y volver
              </button>
            )}
          </div>
        </div>
      )}
      {onVolver && <button type="button" onClick={descartar} disabled={cerrando || agregando} className="min-h-11 rounded border border-rose-300 px-4 text-rose-700">Descartar borrador</button>}
      </fieldset>
    </section>
  );
}
