import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { mensajeDe } from "../../lib/validators";
import { horaLima } from "./mantenimientoTypes";

type Pagina<T> = { items:T[]; total:number; limit:number; offset:number };
type ResultadoHistorico = {
  id:string; ejecucion_id:string|null; origen:"BATCH"|"LEGADO"; calculado_en:string;
  fecha_evaluacion:string|null; fecha_referencia:string|null; tipo_referencia:string|null; vence_en:string|null;
  version_calculo:string; version_dataset:string|null; dataset_sha256:string|null; modelo_sha256:string|null; politica_alerta:string|null;
  dias_vida_util_remanente:number|null; nivel_alerta:string|null; motivo_no_estimable:string|null;
};
type Ejecucion = {
  id:string; iniciado_en:string; finalizado_en:string|null;
  estado:"EN_CURSO"|"COMPLETADA"|"FALLIDA"|"OMITIDA_CONCURRENCIA";
  total:number; estimadas:number; abstenciones:number; error_codigo:string|null;
  version_calculo:string; version_dataset:string; dataset_sha256:string|null; modelo_sha256:string|null; vigencia_horas:number;
  latido_en:string|null;limite_en:string|null;esperados:number|null;procesados:number|null;
};

function Paginacion({offset,limit,total,pendiente,cambiar}: {
  offset:number;limit:number;total:number;pendiente:boolean;cambiar:(valor:number)=>void;
}) {
  return <div className="flex items-center gap-4 text-sm">
    <button type="button" disabled={offset===0 || pendiente} onClick={()=>cambiar(Math.max(0,offset-limit))}>Anterior</button>
    <span>{total===0 ? "0 registros" : `${offset+1}–${Math.min(offset+limit,total)} de ${total}`}</span>
    <button type="button" disabled={offset+limit>=total || pendiente} onClick={()=>cambiar(offset+limit)}>Siguiente</button>
  </div>;
}

export function HistorialRul({serie,onCerrar}:{serie:string;onCerrar:()=>void}) {
  const titulo=useId();
  const [offset,setOffset]=useState(0);
  const consulta=useQuery({queryKey:["historial-rul",serie,offset],
    queryFn:()=>apiFetch<Pagina<ResultadoHistorico>>(`/equipos/${encodeURIComponent(serie)}/historial-rul?limit=20&offset=${offset}`)});
  return <div role="dialog" aria-modal="true" aria-labelledby={titulo} className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-3">
    <div className="max-h-[92vh] w-full max-w-3xl space-y-4 overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
      <div className="flex justify-between gap-4"><h2 id={titulo} className="font-bold">Historial de IA · {serie}</h2>
        <button type="button" onClick={onCerrar}>Cerrar historial</button></div>
      <p className="text-sm text-slate-600">Estos valores muestran lo calculado en cada fecha; no representan una recomendación vigente. El modelo continúa siendo experimental y usa datos sintéticos.</p>
      {consulta.isPending && <p role="status">Cargando historial…</p>}
      {consulta.isError && <div role="alert">{mensajeDe(consulta.error)} <button type="button" onClick={()=>void consulta.refetch()}>Reintentar historial</button></div>}
      {consulta.isSuccess && consulta.data.items.length===0 && <p>Sin cálculos históricos registrados.</p>}
      {(consulta.data?.items ?? []).map((r)=><article key={r.id} className="space-y-1 rounded-lg border border-slate-200 p-3 text-sm">
        <p className="font-semibold">{horaLima(r.calculado_en)} (Lima) · {r.origen==="LEGADO" ? "Registro legado: procedencia incompleta" : "Resultado histórico"}</p>
        <p>{r.dias_vida_util_remanente===null ? `Sin estimación: ${r.motivo_no_estimable ?? "motivo no registrado"}` : `${r.dias_vida_util_remanente} días registrados`}</p>
        <p>Instalación usada: {r.fecha_referencia ?? "desconocida"} · Tipo usado: {r.tipo_referencia ?? "no registrado"}</p>
        <p>Evaluación: {r.fecha_evaluacion ?? "no registrada"} · Vencimiento original: {r.vence_en ? `${horaLima(r.vence_en)} (Lima)` : "no registrado"}</p>
        <details><summary>Procedencia del cálculo</summary>
          <p>Versión: {r.version_calculo} · Dataset: {r.version_dataset ?? "sin procedencia verificada"}</p>
          <p className="break-all">Ejecución: {r.ejecucion_id ?? "no registrada"}</p>
          <p className="break-all">SHA256 del dataset: {r.dataset_sha256 ?? "no registrado"}</p>
          <p className="break-all">Modelo SHA256: {r.modelo_sha256 ?? "sin artefacto registrado"}</p>
          <p>Política: {r.politica_alerta ?? "no registrada"} · Nivel original: {r.nivel_alerta ?? "sin nivel"}</p>
        </details>
      </article>)}
      {consulta.data && <Paginacion offset={offset} limit={20} total={consulta.data.total} pendiente={consulta.isFetching} cambiar={setOffset}/>}
    </div>
  </div>;
}

const ESTADOS={COMPLETADA:"Completada",FALLIDA:"Fallida",OMITIDA_CONCURRENCIA:"Omitida: otra ejecución en curso",EN_CURSO:"Sin cierre confirmado: puede seguir en curso o haberse interrumpido"};

export function EjecucionesRul() {
  const [offset,setOffset]=useState(0);
  const consulta=useQuery({queryKey:["ejecuciones-rul",offset],
    queryFn:()=>apiFetch<Pagina<Ejecucion>>(`/equipos/ejecuciones-rul?limit=5&offset=${offset}`),refetchInterval:60_000});
  return <section aria-label="Ejecuciones de IA" className="space-y-3 rounded-lg border border-slate-200 p-4 text-sm">
    <h2 className="font-bold">Ejecuciones de IA</h2>
    {consulta.isPending && <p role="status">Cargando ejecuciones…</p>}
    {consulta.isError && <div role="alert">{mensajeDe(consulta.error)} <button type="button" onClick={()=>void consulta.refetch()}>Reintentar ejecuciones</button></div>}
    {consulta.isSuccess && consulta.data.items.length===0 && <p>No hay ejecuciones registradas.</p>}
    {(consulta.data?.items ?? []).map((c)=><article key={c.id} className="border-t border-slate-200 pt-2">
      <p>{horaLima(c.iniciado_en)} (Lima) · <strong>{ESTADOS[c.estado]}</strong></p>
      {c.finalizado_en && <p>Finalización: {horaLima(c.finalizado_en)} (Lima)</p>}
      <p>Publicados: {c.total} · Estimaciones: {c.estimadas} · Abstenciones: {c.abstenciones}</p>
      <p>Instantánea esperada: {c.esperados ?? "no registrada"} · Procesados en el intento: {c.procesados ?? "no registrados"}</p>
      <p>Última señal: {c.latido_en ? `${horaLima(c.latido_en)} (Lima)` : "sin supervisión registrada"} · Plazo: {c.limite_en ? `${horaLima(c.limite_en)} (Lima)` : "desconocido"}</p>
      {c.error_codigo && <p>Error registrado: {c.error_codigo}. Revisar la ejecución antes de reintentar.</p>}
      <details><summary>Datos de ejecución</summary><p className="break-all">ID: {c.id}</p>
        <p>Versión: {c.version_calculo} · Dataset: {c.version_dataset} · Vigencia operativa: {c.vigencia_horas} h</p>
        <p className="break-all">SHA256 del dataset: {c.dataset_sha256 ?? "no disponible"}</p>
        <p className="break-all">Modelo SHA256: {c.modelo_sha256 ?? "sin artefacto registrado"}</p></details>
    </article>)}
    {consulta.data && <Paginacion offset={offset} limit={5} total={consulta.data.total} pendiente={consulta.isFetching} cambiar={setOffset}/>}
  </section>;
}
