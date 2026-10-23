import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { mensajeDe } from "../../lib/validators";
import { horaLima } from "./mantenimientoTypes";

type Supervision = {
  estado:"NORMAL"|"ATENCION"|"SIN_EQUIPOS";consultado_en:string;ultima_exitosa_en:string|null;
  total_equipos:number;equipos_sin_evaluar:number;ejecuciones_sin_cierre:number;
  avisos:{codigo:string;severidad:"AVISO"|"INFO";mensaje:string;ejecucion_id:string|null}[];
};

export function SupervisionRul() {
  const gerencia=useAuth().user?.rol==="GERENCIA";
  const consulta=useQuery({queryKey:["supervision-rul"],queryFn:()=>apiFetch<Supervision>("/equipos/supervision-rul"),
    enabled:gerencia,refetchInterval:60_000,refetchOnWindowFocus:"always"});
  if (!gerencia) return null;
  const s=consulta.data;
  return <section aria-label="Supervisión de IA" className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 text-sm">
    <h2 className="font-bold">Supervisión de IA</h2>
    {consulta.isPending && <p>Cargando supervisión…</p>}
    {consulta.isError ? <div role="alert" className="text-rose-800">No se pudo verificar la supervisión: {mensajeDe(consulta.error)} <button type="button" className="underline" onClick={()=>void consulta.refetch()}>Reintentar supervisión</button></div>
      : s && <div role={s.estado==="ATENCION" ? "alert" : undefined} className="space-y-2">
        <p className="font-semibold">{s.estado==="ATENCION" ? "Atención requerida en el proceso de IA" : s.estado==="SIN_EQUIPOS" ? "Sin equipos para evaluar" : "Supervisión al día"}</p>
        <ul className="list-inside list-disc">{s.avisos.map((a,i)=><li key={`${a.codigo}-${a.ejecucion_id??"general"}-${i}`}>
          {a.mensaje} {a.ejecucion_id && <span className="break-all text-xs text-slate-500">Ejecución: {a.ejecucion_id}</span>}
        </li>)}</ul>
        <p>Equipos: {s.total_equipos} · Sin evaluación registrada: {s.equipos_sin_evaluar} · Ejecuciones sin cierre: {s.ejecuciones_sin_cierre}</p>
        <p>Último éxito: {s.ultima_exitosa_en ? `${horaLima(s.ultima_exitosa_en)} (Lima)` : "sin registro"} · Consulta: {horaLima(s.consultado_en)} (Lima)</p>
        <p className="text-xs text-slate-500">Estos avisos supervisan el cálculo automático; no certifican el estado del equipo ni la capacidad predictiva del modelo.</p>
      </div>}
  </section>;
}
