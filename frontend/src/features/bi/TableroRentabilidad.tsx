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
};
type RentabilidadResp = { periodo: string; contratos: ContratoRentabilidad[] };

export function TableroRentabilidad({ periodo }: { periodo: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics", "rentabilidad", periodo],
    queryFn: () => apiFetch<RentabilidadResp>(`/analytics/rentabilidad?periodo=${periodo}`),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="text-xs font-semibold text-slate-400">Cargando rentabilidad…</p>
        </div>
      </div>
    );
  }

  const msg = mensajeDe(error);
  if (msg) {
    return (
      <div role="alert" className="rounded-2xl border border-red-200 bg-red-50/80 p-4 text-sm font-medium text-red-800 shadow-xs">
        {msg}
      </div>
    );
  }

  if (!data || data.contratos.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center shadow-xs">
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
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
      <h2 className="text-base font-bold text-slate-800 mb-2">Rentabilidad por contrato</h2>
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 360 }} />
    </div>
  );
}
