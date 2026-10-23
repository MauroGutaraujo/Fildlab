import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { apiFetch } from "../../api/client";
import { mensajeDe } from "../../lib/validators";
import { echarts } from "./echartsSetup";

type ContratoRentabilidad = {
  contrato_id: number;
  cliente_ruc: string;
  razon_social: string;
  ingreso_soles: string;
  costo_repuestos_soles: string;
  margen_soles: string;
  margen_pct: number | null;
  historial_completo?: boolean;
};
type RentabilidadResp = { periodo: string; contratos: ContratoRentabilidad[] };

export function TableroRentabilidad({ periodo }: { periodo: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics", "rentabilidad", periodo],
    queryFn: () => apiFetch<RentabilidadResp>(`/analytics/rentabilidad?periodo=${periodo}`),
  });

  if (isLoading) {
    return (
      <div role="status" aria-live="polite" className="flex items-center justify-center rounded-xl border border-slate-200 bg-white p-8">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-500">Cargando rentabilidad…</p>
        </div>
      </div>
    );
  }

  const msg = mensajeDe(error);
  if (msg) {
    return (
      <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-800">
        {msg}
      </div>
    );
  }

  if (!data || data.contratos.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <p className="text-sm font-medium text-slate-500">Sin datos disponibles para el periodo</p>
      </div>
    );
  }

  const option = {
    tooltip: { trigger: "axis" },
    legend: { data: ["Ingreso", "Costo de repuestos", "Margen %"] },
    xAxis: { type: "category", data: data.contratos.map((c) => c.razon_social) },
    yAxis: [
      { type: "value", name: "S/." },
      { type: "value", name: "%", max: 100 },
    ],
    series: [
      { name: "Ingreso", type: "bar", data: data.contratos.map((c) => Number(c.ingreso_soles)) },
      { name: "Costo de repuestos", type: "bar", data: data.contratos.map((c) => Number(c.costo_repuestos_soles)) },
      { name: "Margen %", type: "line", yAxisIndex: 1, data: data.contratos.map((c) => c.margen_pct) },
    ],
  };

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Contratos y repuestos</p>
        <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900">Rentabilidad por contrato</h2>
        <p className="mt-2 text-sm text-slate-600">Margen contractual mensual menos repuestos de órdenes liquidadas. No incluye mano de obra, prorrateo ni ventas.</p>
        {data.contratos.some((c) => !c.historial_completo) && <p role="note" className="mt-2 text-sm text-amber-800">Hay datos heredados sin historial completo de tarifas o costos; sus márgenes son estimaciones.</p>}
      </div>
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 360 }} />
    </div>
  );
}
