import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react/lib/core";
import { apiFetch } from "../../api/client";
import { DataTable } from "../../components/DataTable";
import { ClienteIdentidad } from "../../components/ClienteIdentidad";
import { mensajeDe } from "../../lib/validators";
import { echarts } from "./echartsSetup";
import { useClientesLookup } from "../clientes/useClientesLookup";

type OrdenFueraSla = {
  orden_id: string;
  equipo_serie: string | null;
  razon_social: string;
  tiempo_respuesta_horas: string;
  sla_horas_max_respuesta: number;
};
type SlaResp = {
  periodo: string;
  total_ordenes: number;
  ordenes_sin_medicion: number;
  ordenes_fuera_sla: OrdenFueraSla[];
  pct_cumplimiento: number | null;
};

export function TableroSla({ periodo }: { periodo: string }) {
  const clientes = useClientesLookup();
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics", "sla", periodo],
    queryFn: () => apiFetch<SlaResp>(`/analytics/sla?periodo=${periodo}`),
  });

  if (isLoading) {
    return (
      <div role="status" aria-live="polite" className="flex items-center justify-center rounded-xl border border-slate-200 bg-white p-8">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-500">Cargando SLA…</p>
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

  if (!data || data.total_ordenes === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <p className="text-sm font-medium text-slate-500">Sin datos disponibles para el periodo</p>
      </div>
    );
  }

  if (data.pct_cumplimiento === null) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-8 text-center">
        <p className="text-sm font-medium text-amber-900">
          Ninguna de las {data.total_ordenes} órdenes del periodo tiene tiempo de respuesta medido todavía.
        </p>
      </div>
    );
  }

  const pct = data.pct_cumplimiento;
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
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Atención de órdenes</p>
        <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-900">Cumplimiento de SLA</h2>
      </div>
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 280 }} />
      {data.ordenes_sin_medicion > 0 && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
          {data.ordenes_sin_medicion} orden(es) sin tiempo de respuesta medido, excluidas del cálculo.
        </p>
      )}
      {data.ordenes_fuera_sla.length > 0 ? (
        <DataTable
          rows={data.ordenes_fuera_sla}
          rowKey={(o) => o.orden_id}
          columns={[
            { header: "Equipo", cell: (o) => o.equipo_serie ?? "—" },
            { header: "Cliente", cell: (o) => <ClienteIdentidad razonSocial={o.razon_social} ruc={clientes.porRazonSocial(o.razon_social)?.ruc} /> },
            { header: "Tiempo de respuesta (h)", cell: (o) => o.tiempo_respuesta_horas },
            { header: "SLA máximo (h)", cell: (o) => o.sla_horas_max_respuesta },
          ]}
        />
      ) : (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">Ninguna orden excedió el SLA en este periodo.</p>
      )}
    </div>
  );
}
