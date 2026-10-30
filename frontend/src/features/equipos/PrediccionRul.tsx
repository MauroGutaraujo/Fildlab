export type NivelAlerta = "VERDE" | "AMARILLO" | "ROJO";
export type PrediccionRul = {
  equipo_serie: string;
  dias_vida_util_remanente: number | null;
  nivel_alerta: NivelAlerta | null;
  actualizado_en: string;
  estado_estimacion: "ESTIMADA" | "NO_ESTIMABLE" | "REQUIERE_RECALCULO" | "VENCIDA";
  motivo_no_estimable: string | null;
  version_calculo: string;
  version_dataset: string | null;
  experimental: boolean;
  origen_datos: "SINTETICOS";
  politica_alerta: string;
  fecha_referencia: string | null;
  tipo_referencia: string | null;
  ejecucion_id: string | null;
  vence_en: string | null;
  alcance_estimacion: "SISTEMA_DESDE_INSTALACION" | null;
};

const ALERTAS = {
  VERDE: { label: "Sin acción requerida", color: "border-emerald-200 bg-emerald-50 text-emerald-800" },
  AMARILLO: { label: "Programar revisión", color: "border-amber-200 bg-amber-50 text-amber-900" },
  ROJO: { label: "Mantenimiento urgente", color: "border-rose-200 bg-rose-50 text-rose-800" },
};

const MOTIVOS: Record<string, string> = {
  MODELO_INESTABLE: "Sin estimación: el ajuste del modelo requiere revisión.",
  EDAD_FUERA_SOPORTE: "Sin estimación: la antigüedad supera el período observado.",
  MEDIANA_FUERA_SOPORTE: "Sin estimación: no hay datos suficientes para este horizonte.",
  FECHA_FUTURA: "Sin estimación: revisa la fecha de instalación del sistema.",
  TIPO_DESCONOCIDO: "Sin estimación: tipo de sistema sin modelo disponible.",
};

type Estimada = PrediccionRul & { dias_vida_util_remanente: number; nivel_alerta: NivelAlerta };
export function esEstimacion(p: PrediccionRul | undefined, ahora = Date.now()): p is Estimada {
  return p?.estado_estimacion === "ESTIMADA" && p.motivo_no_estimable == null
    && !!p.ejecucion_id && !!p.tipo_referencia && !!p.vence_en
    && Number.isFinite(Date.parse(p.actualizado_en)) && Date.parse(p.actualizado_en) <= ahora
    && Date.parse(p.vence_en) > ahora && Date.parse(p.vence_en) > Date.parse(p.actualizado_en)
    && typeof p.dias_vida_util_remanente === "number" && Number.isInteger(p.dias_vida_util_remanente)
    && p.dias_vida_util_remanente >= 0
    && (p.nivel_alerta === "VERDE" || p.nivel_alerta === "AMARILLO" || p.nivel_alerta === "ROJO");
}

// Reevalúa también sin tráfico: al vencer la primera fila o al cabo de un minuto.
export function useRelojRul(predicciones: PrediccionRul[] | undefined) {
  const [ahora, setAhora] = useState(Date.now);
  const vencimientos = (predicciones ?? []).map((p) => p.vence_en).join(",");
  useEffect(() => {
    const pendientes = vencimientos.split(",").map((s) => Date.parse(s) - Date.now()).filter((n) => n > 0);
    const timer = window.setTimeout(() => setAhora(Date.now()), Math.max(1, Math.min(60_000, ...pendientes)));
    return () => window.clearTimeout(timer);
  }, [ahora, vencimientos]);
  return ahora;
}

export function ResultadoRul({ prediccion: p }: { prediccion: PrediccionRul | undefined }) {
  const estado = esEstimacion(p) ? ALERTAS[p.nivel_alerta] : null;
  const sinEstimacion = !p ? "Sin evaluar"
    : p.estado_estimacion === "REQUIERE_RECALCULO" ? "Recálculo pendiente"
    : p.estado_estimacion === "VENCIDA" || (p.vence_en && Date.parse(p.vence_en) <= Date.now()) ? "Estimación vencida"
    : p.estado_estimacion === "NO_ESTIMABLE" ? MOTIVOS[p.motivo_no_estimable ?? ""] ?? "Sin estimación disponible"
    : "Recálculo pendiente";
  return <>
    {estado ? <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${estado.color}`}>
      <span aria-hidden="true" className="h-2 w-2 rounded-full bg-current" />
      {p?.dias_vida_util_remanente} días estimados · {estado.label}
    </span> : <span className="inline-block rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600">
      {sinEstimacion}
    </span>}
  </>;
}
import { useEffect, useState } from "react";
