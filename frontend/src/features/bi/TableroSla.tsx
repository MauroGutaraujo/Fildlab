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

type OrdenMedible = { contrato_id: number; fecha_creacion_cliente: string; tiempo_respuesta_horas: string | null };
type ContratoSla = { id: number; sla_horas_max_respuesta: number };

function mesLima(fecha: string) {
  const partes = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Lima", year: "numeric", month: "2-digit" }).formatToParts(new Date(fecha));
  return `${partes.find((p) => p.type === "year")?.value}-${partes.find((p) => p.type === "month")?.value}`;
}

export function TableroSla({ periodo }: { periodo: string }) {
  const clientes = useClientesLookup();
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics", "sla", periodo],
    queryFn: () => apiFetch<SlaResp>(`/analytics/sla?periodo=${periodo}`),
  });
  const ordenes = useQuery({
    queryKey: ["bi", "sla-ordenes", periodo],
    queryFn: () => apiFetch<OrdenMedible[]>("/ordenes"),
  });
  const contratos = useQuery({
    queryKey: ["bi", "sla-contratos"],
    queryFn: () => apiFetch<ContratoSla[]>("/contratos"),
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

  const pct = data.pct_cumplimiento;
  const enNorma = pct !== null && pct >= 98;
  const color = enNorma ? "#059669" : (pct ?? 0) < 90 ? "#dc2626" : "#d97706";
  const mediblesDelPeriodo = (ordenes.data ?? []).filter((o) => {
    const valor = Number(o.tiempo_respuesta_horas);
    return mesLima(o.fecha_creacion_cliente) === periodo && Number.isFinite(valor) && o.tiempo_respuesta_horas !== null;
  });
  const promedio = mediblesDelPeriodo.length
    ? mediblesDelPeriodo.reduce((s, o) => s + Number(o.tiempo_respuesta_horas), 0) / mediblesDelPeriodo.length
    : null;
  const slaPorContrato = new Map((contratos.data ?? []).map((c) => [c.id, c.sla_horas_max_respuesta]));
  const limitesConocidos = mediblesDelPeriodo
    .map((o) => slaPorContrato.get(o.contrato_id))
    .filter((sla): sla is number => typeof sla === "number" && Number.isFinite(sla) && sla > 0);
  const promedioPactado = limitesConocidos.length
    ? limitesConocidos.reduce((s, sla) => s + sla, 0) / limitesConocidos.length
    : null;
  const medidos = Math.max(0, data.total_ordenes - data.ordenes_sin_medicion);
  const retrasos = data.ordenes_fuera_sla.length;
  const aTiempo = Math.max(0, medidos - retrasos);
  const option = {
    series: [
      {
        type: "gauge",
        min: 0,
        max: 100,
        startAngle: 180,
        endAngle: 0,
        pointer: { show: false },
        progress: { show: true, width: 18, roundCap: true, itemStyle: { color } },
        axisLine: { lineStyle: { width: 18, color: [[1, "#e2e8f0"]] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: { formatter: "{value}%", fontSize: 25, fontWeight: "bold", offsetCenter: [0, "-5%"], color: "#0f172a" },
        data: [{ value: pct === null ? 0 : Math.round(pct * 100) / 100, name: "Cumplimiento SLA" }],
      },
    ],
  };

  return (
    <div className="space-y-4">
      <section className={`grid items-center gap-4 rounded-2xl border p-4 shadow-sm sm:grid-cols-[minmax(0,1fr)_minmax(230px,0.8fr)] sm:p-6 ${enNorma ? "border-emerald-200 bg-gradient-to-br from-white to-emerald-50" : "border-amber-200 bg-gradient-to-br from-white to-amber-50"}`}>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Atención de órdenes</p>
          <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-950">Cumplimiento de SLA</h2>
          <p className={`mt-3 inline-flex rounded-full border px-3 py-1.5 text-sm font-semibold ${enNorma ? "border-emerald-200 bg-emerald-100 text-emerald-900" : "border-amber-200 bg-amber-100 text-amber-900"}`}>
            {pct === null ? "Sin mediciones de SLA" : enNorma ? "SLA en Norma (Meta > 98%)" : "Riesgo de Penalización Contractual"}
          </p>
          <p className="mt-2 text-sm text-slate-600">Meta corporativa: mantener los servicios fuera de SLA por debajo del 2% (cumplimiento ≥ 98%).</p>
        </div>
        {pct === null ? (
          <div className="rounded-xl border border-amber-200 bg-white/80 p-5 text-sm text-amber-900">
            Ninguna de las {data.total_ordenes} órdenes del periodo tiene tiempo de respuesta medido todavía.
          </div>
        ) : <ReactEChartsCore echarts={echarts} option={option} style={{ height: 190, width: "100%" }} />}
      </section>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Tiempos de atención</p>
          <h3 className="mt-1 text-base font-bold text-slate-900">Tiempo Promedio de Respuesta</h3>
          {ordenes.isLoading ? (
            <p className="mt-4 text-sm text-slate-500">Calculando el promedio…</p>
          ) : ordenes.isError ? (
            <p role="status" className="mt-4 text-sm text-amber-800">No se pudieron cargar los datos de órdenes para calcular el tiempo promedio.</p>
          ) : promedio !== null ? (
            <>
              <p className="mt-4 text-2xl font-bold tabular-nums text-slate-950">{promedio.toFixed(1)} h <span className="text-sm font-medium text-slate-500">{contratos.isLoading ? "calculando SLA pactado…" : promedioPactado !== null ? `de ${promedioPactado.toFixed(1)} h pactadas` : "SLA pactado no disponible"}</span></p>
              {promedioPactado !== null && limitesConocidos.length !== mediblesDelPeriodo.length && <p className="mt-1 text-xs text-slate-500">SLA pactado promedio calculado para {limitesConocidos.length} de {mediblesDelPeriodo.length} servicios medidos.</p>}
              {contratos.isError && <p className="mt-1 text-xs text-amber-800">No se pudieron cargar los contratos para comparar con el SLA pactado.</p>}
            </>
          ) : <p className="mt-4 text-sm text-slate-500">Sin tiempos medidos disponibles para este periodo.</p>}
          {promedio !== null && <p className="mt-1 text-xs text-slate-500">Promedio de {mediblesDelPeriodo.length} orden(es) con medición.</p>}
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Resumen del periodo</p>
          <h3 className="mt-1 text-base font-bold text-slate-900">Desglose de Servicios</h3>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <p className="rounded-lg bg-slate-50 p-3"><strong className="block text-lg text-slate-950">{data.total_ordenes}</strong>órdenes atendidas</p>
            <p className="rounded-lg bg-emerald-50 p-3"><strong className="block text-lg text-emerald-800">{aTiempo}</strong>servicios a tiempo</p>
            <p className="rounded-lg bg-rose-50 p-3"><strong className="block text-lg text-rose-800">{retrasos}</strong>servicios con retraso</p>
            <p className="rounded-lg bg-amber-50 p-3"><strong className="block text-lg text-amber-800">{data.ordenes_sin_medicion}</strong>sin medición</p>
          </div>
        </section>
      </div>
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
        <p className={`rounded-lg border px-3 py-2 text-sm font-medium ${enNorma ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
          {enNorma ? "Ninguna orden excedió el SLA en este periodo." : "El cumplimiento está bajo la meta corporativa; revisar el desglose y las órdenes del periodo."}
        </p>
      )}
    </div>
  );
}
