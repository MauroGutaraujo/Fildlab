import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { TextAreaField } from "../../components/FormField";
import { mensajeDe } from "../../lib/validators";
import { horaLima, TRABAJOS, type CambioComponente, type Intervencion } from "./mantenimientoTypes";

function AnularRegistro({ ruta, onCancelar, onGuardar }: { ruta: string; onCancelar: () => void; onGuardar: () => void }) {
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const anular = useMutation({ mutationFn: () => apiFetch(ruta, { method: "POST", body: { motivo: motivo.trim() } }), onSuccess: onGuardar });
  return <form className="mt-3 space-y-2" onSubmit={(e) => {
    e.preventDefault(); setError(null);
    if (!motivo.trim()) return setError("Indica el motivo de anulación");
    if (!anular.isPending) anular.mutate();
  }}>
    <TextAreaField label="Motivo de anulación" value={motivo} maxLength={2000} onChange={(e) => setMotivo(e.target.value)} />
    {(error || anular.error) && <p role="alert" className="text-rose-700">{error ?? mensajeDe(anular.error)}</p>}
    <button type="submit" disabled={anular.isPending} className="mr-4 text-sm font-semibold text-rose-700 disabled:opacity-50">Confirmar anulación</button>
    <button type="button" onClick={onCancelar} className="text-sm text-slate-600">Cancelar anulación</button>
  </form>;
}

export function HistorialComponente({ base, componenteId, puedeEscribir, onCambio }: {
  base: string; componenteId: string; puedeEscribir: boolean; onCambio: (mensaje: string) => void;
}) {
  const [anulando, setAnulando] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const ruta = `${base}/componentes/${componenteId}/intervenciones`;
  const historial = useQuery({ queryKey: ["intervenciones", base, componenteId], queryFn: () => apiFetch<Intervencion[]>(ruta) });
  const cambios = useQuery({ queryKey: ["cambios-componente", base, componenteId, offset],
    queryFn: () => apiFetch<CambioComponente[]>(`${base}/componentes/${componenteId}/cambios?limit=20&offset=${offset}`) });
  return <div className="space-y-3">
    <h3 className="font-semibold text-slate-900">Historial de intervenciones</h3>
    {historial.isPending && <p role="status">Cargando historial…</p>}
    {historial.isError && <div role="alert">{mensajeDe(historial.error)} <button type="button" onClick={() => void historial.refetch()}>Reintentar historial</button></div>}
    {historial.isSuccess && historial.data.length === 0 && <p className="text-sm text-slate-500">Sin intervenciones registradas</p>}
    <ol className="space-y-3">{(historial.data ?? []).map((i) => <li key={i.id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
      <p className="font-semibold">{i.fecha_efectiva} · {TRABAJOS[i.tipo]} {i.anulacion && <span className="ml-2 text-rose-700">Anulada</span>}</p>
      <p className="whitespace-pre-wrap text-slate-700">{i.observacion}</p>
      <p className="mt-1 text-xs text-slate-500">Registrado por {i.registrado_por_nombre} · {horaLima(i.registrado_en)} (Lima)</p>
      <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer">Orden y evidencia asociada</summary>
        <p className="break-all">Orden: {i.orden_id}</p><p className="break-all">Hash del acta: {i.acta_hash}</p>
      </details>
      {i.anulacion ? <p className="mt-2 text-rose-700">Motivo: {i.anulacion.motivo} · Usuario #{i.anulacion.registrado_por_id} · {horaLima(i.anulacion.registrado_en)} (Lima)</p>
        : puedeEscribir && (anulando === i.id ? <AnularRegistro ruta={`${ruta}/${i.id}/anular`} onCancelar={() => setAnulando(null)} onGuardar={() => {setAnulando(null); onCambio("Anulación registrada");}} />
          : <button type="button" className="mt-2 text-xs font-semibold text-rose-700" onClick={() => setAnulando(i.id)}>Anular registro</button>)}
    </li>)}</ol>
    <section aria-labelledby={`cambios-${componenteId}`} className="space-y-2 border-t border-slate-200 pt-3">
      <h3 id={`cambios-${componenteId}`} className="font-semibold text-slate-900">Historial administrativo de ficha</h3>
      {cambios.isPending && <p role="status">Cargando cambios…</p>}
      {cambios.isError && <div role="alert">{mensajeDe(cambios.error)} <button type="button" onClick={() => void cambios.refetch()}>Reintentar cambios</button></div>}
      {cambios.isSuccess && cambios.data.length === 0 && <p className="text-sm text-slate-500">Sin correcciones ni cambios de estado</p>}
      <ol className="space-y-2">{(cambios.data ?? []).map((c) => <li key={c.solicitud_id} className="rounded-lg border border-slate-200 p-3 text-sm">
        <p className="font-semibold">{c.accion === "CORREGIR" ? "Ficha corregida" : c.accion === "ANULAR_ALTA" ? "Alta anulada" : "Alta restablecida"} · revisión {c.revision_anterior} → {c.revision_nueva}</p>
        <p className="text-slate-700">Motivo: {c.motivo}</p>
        <p className="text-xs text-slate-500">Gerencia #{c.registrado_por_id} · {horaLima(c.registrado_en)} (Lima)</p>
        <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer">Ver ficha anterior y posterior</summary>
          <p className="mt-1 font-semibold">Antes</p><pre className="overflow-x-auto whitespace-pre-wrap">{JSON.stringify(c.antes, null, 2)}</pre>
          <p className="mt-1 font-semibold">Después</p><pre className="overflow-x-auto whitespace-pre-wrap">{JSON.stringify(c.despues, null, 2)}</pre>
        </details>
      </li>)}</ol>
      <div className="flex gap-3 text-xs">
        <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Cambios anteriores</button>
        <button type="button" disabled={(cambios.data?.length ?? 0) < 20} onClick={() => setOffset(offset + 20)}>Más cambios</button>
      </div>
    </section>
  </div>;
}
