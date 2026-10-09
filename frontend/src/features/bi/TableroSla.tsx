import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { apiFetch } from "../../api/client";
import { DataTable } from "../../components/DataTable";
import { mensajeDe } from "../../lib/validators";
import { echarts } from "./echartsSetup";

type OrdenFueraSla = {
  orden_id: string;
  equipo_serie: string | null;
  razon_social: string;
  tiempo_respuesta_horas: string;
  sla_horas_max_respuesta: number;
};
type SlaResp = { periodo: string; total_ordenes: number; ordenes_fuera_sla: OrdenFueraSla[]; pct_cumplimiento: number | null };

export function TableroSla({ periodo }: { periodo: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics", "sla", periodo],
    queryFn: () => apiFetch<SlaResp>(`/analytics/sla?periodo=${periodo}`),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="text-xs font-semibold text-slate-400">Cargando SLA…</p>
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

  if (!data || data.total_ordenes === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center shadow-xs">
        <p className="text-sm font-medium text-slate-500">Sin datos disponibles para el periodo</p>
      </div>
    );
  }

  const pct = data.pct_cumplimiento ?? 0;
  const option = {
    series: [
      {
        type: "gauge",
        min: 0,
        max: 100,
        axisLine: { lineStyle: { width: 18, color: [[0.98, "#dc2626"], [1, "#16a34a"]] } },
        detail: { formatter: "{value}%", fontSize: 22 },
        data: [{ value: Math.round(pct * 100) / 100, name: "Cumplimiento SLA" }],
      },
    ],
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
      <h2 className="text-base font-bold text-slate-800 mb-2">Cumplimiento de SLA</h2>
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 280 }} />
      {data.ordenes_fuera_sla.length > 0 ? (
        <DataTable
          rows={data.ordenes_fuera_sla}
          rowKey={(o) => o.orden_id}
          columns={[
            { header: "Equipo", cell: (o) => o.equipo_serie ?? "—" },
            { header: "Cliente", cell: (o) => o.razon_social },
            { header: "Tiempo de respuesta (h)", cell: (o) => o.tiempo_respuesta_horas },
            { header: "SLA máximo (h)", cell: (o) => o.sla_horas_max_respuesta },
          ]}
        />
      ) : (
        <p className="mt-3 text-sm font-medium text-emerald-700">Ninguna orden excedió el SLA en este periodo.</p>
      )}
    </div>
  );
}
