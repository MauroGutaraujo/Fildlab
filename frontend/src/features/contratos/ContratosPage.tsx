import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { DataTable } from "../../components/DataTable";
import { FormField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { errorMonto, errorRuc, errorSla, mensajeDe } from "../../lib/validators";

type Contrato = {
  id: number;
  cliente_ruc: string;
  fecha_inicio: string;
  fecha_fin: string;
  monto_mensual_soles: string;
  sla_horas_max_respuesta: number;
  estado: string;
};
type Errores = Partial<Record<"ruc" | "inicio" | "fin" | "monto" | "sla", string>>;

function EstadoContrato({ estado }: { estado: string }) {
  const color = estado === "ACTIVO"
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : estado === "ANULADO"
      ? "border-slate-200 bg-slate-100 text-slate-600"
      : "border-amber-200 bg-amber-50 text-amber-800";
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${color}`}>{estado}</span>;
}

export function ContratosPage() {
  const puedeEscribir = useAuth().user?.rol === "GERENCIA"; // RN-01
  const qc = useQueryClient();
  const { data = [], isLoading, error } = useQuery({ queryKey: ["contratos"], queryFn: () => apiFetch<Contrato[]>("/contratos") });

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Contrato | null>(null);
  const [ruc, setRuc] = useState("");
  const [inicio, setInicio] = useState("");
  const [fin, setFin] = useState("");
  const [monto, setMonto] = useState("");
  const [sla, setSla] = useState("4");
  const [errores, setErrores] = useState<Errores>({});

  const invalidar = () => qc.invalidateQueries({ queryKey: ["contratos"] });

  const guardar = useMutation({
    mutationFn: () => {
      const vigencia = {
        fecha_inicio: inicio,
        fecha_fin: fin,
        monto_mensual_soles: monto.trim(),
        sla_horas_max_respuesta: Number(sla),
      };
      return editando
        ? apiFetch<Contrato>(`/contratos/${editando.id}`, { method: "PUT", body: vigencia })
        : apiFetch<Contrato>("/contratos", { method: "POST", body: { cliente_ruc: ruc, ...vigencia } });
    },
    onSuccess: async () => {
      await invalidar();
      cerrar();
    },
  });

  const anular = useMutation({
    mutationFn: (id: number) => apiFetch<Contrato>(`/contratos/${id}/anular`, { method: "POST" }),
    onSuccess: invalidar,
  });

  function abrir(c: Contrato | null) {
    guardar.reset();
    setErrores({});
    setEditando(c);
    setRuc(c?.cliente_ruc ?? "");
    setInicio(c?.fecha_inicio ?? "");
    setFin(c?.fecha_fin ?? "");
    setMonto(c?.monto_mensual_soles ?? "");
    setSla(String(c?.sla_horas_max_respuesta ?? 4));
    setAbierto(true);
  }

  function cerrar() {
    setAbierto(false);
    setEditando(null);
  }

  function enviar() {
    const e: Errores = {};
    if (!editando) {
      const r = errorRuc(ruc);
      if (r) e.ruc = r;
    }
    if (!inicio) e.inicio = "La fecha de inicio es obligatoria";
    if (!fin) e.fin = "La fecha de fin es obligatoria";
    else if (inicio && fin < inicio) e.fin = "La fecha de fin no puede ser anterior al inicio";
    const m = errorMonto(monto);
    if (m) e.monto = m;
    const s = errorSla(sla);
    if (s) e.sla = s;
    setErrores(e);
    if (Object.keys(e).length === 0) guardar.mutate();
  }

  const editable = (c: Contrato) => puedeEscribir && c.estado !== "ANULADO";

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">Auditoría de servicio</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">Contratos y SLA</h1>
          <p className="mt-1 text-sm text-slate-500">Vigencias, compromisos de respuesta y estado contractual.</p>
        </div>
        {puedeEscribir && !abierto && (
          <button type="button" onClick={() => abrir(null)} className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
            Nuevo contrato
          </button>
        )}
      </div>

      {abierto && (
        <FormPanel
          title={editando ? `Editar contrato ${editando.id}` : "Nuevo contrato"}
          onSubmit={enviar}
          onCancel={cerrar}
          saving={guardar.isPending}
          error={mensajeDe(guardar.error)}
        >
          <FormField label="RUC del cliente" value={ruc} onChange={(e) => setRuc(e.target.value)} disabled={!!editando} inputMode="numeric" error={errores.ruc} />
          <FormField label="Inicio de vigencia" type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} error={errores.inicio} />
          <FormField label="Fin de vigencia" type="date" value={fin} onChange={(e) => setFin(e.target.value)} error={errores.fin} />
          <FormField label="Monto mensual (S/)" value={monto} onChange={(e) => setMonto(e.target.value)} inputMode="decimal" error={errores.monto} />
          <FormField label="SLA máx. respuesta (horas)" value={sla} onChange={(e) => setSla(e.target.value)} inputMode="numeric" error={errores.sla} />
        </FormPanel>
      )}

      {anular.error && (
        <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-medium text-rose-800">
          {mensajeDe(anular.error)}
        </p>
      )}

      <DataTable
        rows={data}
        rowKey={(c) => c.id}
        loading={isLoading}
        error={mensajeDe(error)}
        onEdit={puedeEscribir ? abrir : undefined}
        canEdit={editable}
        actions={(c) =>
          editable(c) && (
            <button
              type="button"
              className="text-red-700 hover:underline"
              onClick={() => window.confirm(`¿Anular el contrato ${c.id}?`) && anular.mutate(c.id)}
            >
              Anular
            </button>
          )
        }
        columns={[
          { header: "Cliente (RUC)", cell: (c) => c.cliente_ruc },
          { header: "Vigencia", cell: (c) => `${c.fecha_inicio} → ${c.fecha_fin}` },
          { header: "Monto mensual", cell: (c) => `S/ ${c.monto_mensual_soles}` },
          { header: "SLA", cell: (c) => `${c.sla_horas_max_respuesta} h` },
          { header: "Estado", cell: (c) => <EstadoContrato estado={c.estado} /> },
        ]}
      />
    </section>
  );
}
