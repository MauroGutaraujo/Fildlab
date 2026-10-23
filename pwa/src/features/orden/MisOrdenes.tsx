import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { db } from "../../db/dexie";
import { EVENTO_OUTBOX } from "../../db/outbox";
import { admiteReintentoManual, exportarOrden, reintentarOrden } from "../../db/recuperacion";

const ETIQUETA_ESTADO: Record<string, string> = {
  pendiente: "Pendiente de sincronizar",
  sincronizando: "Sincronizando…",
  sincronizada: "Sincronizada",
  error: "Error",
  borrador: "Borrador",
};

/** Review Focus 3 / spec §3.6: las órdenes en error deben quedar visibles, nunca desaparecer
 * en silencio (RNF-04). Se lee vía TanStack Query para poder invalidarse desde "Sincronizar
 * ahora" (App.tsx) y refrescar la lista automáticamente tras cada pasada del Outbox. */
export function MisOrdenes({ tecnicoId }: { tecnicoId: number }) {
  const qc = useQueryClient();
  const [accion, setAccion] = useState<{ tecnicoId: number; id: string } | null>(null);
  const [errorAccion, setErrorAccion] = useState<{ tecnicoId: number; mensaje: string } | null>(null);
  async function recuperar(id: string, exportar: boolean) {
    setAccion({ tecnicoId, id });
    setErrorAccion(null);
    try {
      if (exportar) {
        const contenido = await exportarOrden(id, tecnicoId);
        const url = URL.createObjectURL(new Blob([contenido], { type: "application/json;charset=utf-8" }));
        const enlace = document.createElement("a");
        try {
          enlace.href = url;
          enlace.download = `orden-${id}.json`;
          document.body.appendChild(enlace);
          enlace.click();
        } finally {
          enlace.remove();
          URL.revokeObjectURL(url);
        }
      } else {
        await reintentarOrden(id, tecnicoId);
      }
    } catch (e) {
      setErrorAccion({ tecnicoId, mensaje: e instanceof Error ? e.message : "No se pudo completar la acción. Intenta nuevamente" });
    } finally {
      setAccion(null);
      await qc.invalidateQueries({ queryKey: ["ordenesLocal", tecnicoId] });
    }
  }
  useEffect(() => {
    const refrescar = () => { void qc.invalidateQueries({ queryKey: ["ordenesLocal", tecnicoId] }); };
    window.addEventListener(EVENTO_OUTBOX, refrescar);
    return () => window.removeEventListener(EVENTO_OUTBOX, refrescar);
  }, [qc, tecnicoId]);
  const { data: ordenes = [] } = useQuery({
    queryKey: ["ordenesLocal", tecnicoId],
    queryFn: async () => (await db.ordenesLocal.where("tecnico_id").equals(tecnicoId).toArray()).sort((a, b) => b.creado_en_local.localeCompare(a.creado_en_local)),
  });

  return (
    <section className="space-y-4 p-4 pb-28">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Trabajo de campo</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Mis órdenes</h1>
        <p className="mt-1 text-sm text-slate-600">Consulta el estado de guardado y sincronización de tus servicios.</p>
      </header>
      {errorAccion?.tecnicoId === tecnicoId && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{errorAccion.mensaje}</p>}
      {ordenes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center">
          <p className="font-semibold text-slate-800">No hay órdenes registradas</p>
          <p className="mt-1 text-sm text-slate-500">Las órdenes que completes en este dispositivo aparecerán aquí.</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {ordenes.map((o) => (
            <li key={o.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="font-mono font-semibold text-slate-700">{o.id.slice(0, 8)}</span>
                <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                  o.estado_sync === "error" ? "border-rose-200 bg-rose-50 text-rose-800"
                    : o.estado_sync === "sincronizada" ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-blue-200 bg-blue-50 text-blue-800"
                }`}>
                  {ETIQUETA_ESTADO[o.estado_sync] ?? o.estado_sync}
                </span>
              </div>
              <p className="mt-2 text-sm font-medium text-slate-900">Equipo {o.equipo_serie}</p>
              <p className="mt-0.5 text-xs text-slate-500">Intervención {o.tipo_intervencion}</p>
              {o.error_detalle && <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{o.error_detalle}</p>}
              {o.estado_sync === "error" && <div className="mt-3 space-y-2">
                <p className="text-xs text-slate-600">Exportar JSON guarda una copia local con la firma y los datos de esta orden. Funciona sin conexión, incluso con el turno vencido.</p>
                <p className="text-xs text-slate-600">{admiteReintentoManual(o)
                  ? "Pide a Gerencia resolver la causa antes de reintentar el envío. Se conserva el acta original."
                  : "Esta orden requiere revisión. Exporta el JSON original para Gerencia; el acta firmada no se modifica."}</p>
                <div className="flex flex-wrap gap-3">
                  <button type="button" disabled={accion?.tecnicoId === tecnicoId} onClick={() => void recuperar(o.id, true)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold disabled:opacity-50">Exportar JSON</button>
                  {admiteReintentoManual(o) && <button type="button" disabled={accion?.tecnicoId === tecnicoId} onClick={() => void recuperar(o.id, false)} className="rounded-lg bg-blue-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Reintentar envío</button>}
                </div>
              </div>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
