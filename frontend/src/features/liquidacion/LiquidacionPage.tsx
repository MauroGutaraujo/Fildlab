import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiFetch } from "../../api/client";
import { DataTable } from "../../components/DataTable";
import { FormField, SelectField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { fechaHora, mensajeDe } from "../../lib/validators";

const ESTADOS = ["SINCRONIZADA", "COMPROMETIDA", "LIQUIDADA"] as const;
type Orden = {
  id: string;
  equipo_serie: string | null;
  tipo_intervencion: string;
  estado: (typeof ESTADOS)[number];
  fecha_sincronizacion: string;
};
type Adenda = { id: number; observacion: string; ajuste_repuestos: { repuesto_codigo: string; delta: number }[] | null; fecha_adenda: string };
type Acta = {
  hash_sha256: string;
  previous_hash: string | null;
  firma_base64: string;
  gps_latitud: string;
  gps_longitud: string;
  creado_en: string;
};
type Errores = Partial<Record<"obs" | "codigo" | "delta", string>>;

const DELTA_RE = /^[+-]?[1-9][0-9]*$/;

function EstadoOrden({ estado }: { estado: Orden["estado"] }) {
  const color = estado === "LIQUIDADA"
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : estado === "COMPROMETIDA"
      ? "border-amber-200 bg-amber-50 text-amber-800"
      : "border-sky-200 bg-sky-50 text-sky-800";
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${color}`}>{estado}</span>;
}

export function LiquidacionPage() {
  const qc = useQueryClient();
  const [estado, setEstado] = useState("");
  const ordenes = useQuery({
    queryKey: ["ordenes", estado],
    queryFn: () => apiFetch<Orden[]>(estado ? `/ordenes?estado=${estado}` : "/ordenes"),
  });

  const [enAdenda, setEnAdenda] = useState<Orden | null>(null);
  const [obs, setObs] = useState("");
  const [codigo, setCodigo] = useState("");
  const [delta, setDelta] = useState("");
  const [errores, setErrores] = useState<Errores>({});

  const previas = useQuery({
    queryKey: ["adendas", enAdenda?.id],
    queryFn: () => apiFetch<Adenda[]>(`/ordenes/${enAdenda!.id}/adendas`),
    enabled: enAdenda !== null,
  });

  // RN-04: el acta firmada se muestra en solo lectura; nunca se edita desde aquí.
  const acta = useQuery({
    queryKey: ["acta", enAdenda?.id],
    queryFn: () => apiFetch<Acta>(`/ordenes/${enAdenda!.id}/acta`),
    enabled: enAdenda !== null,
    retry: false,
  });
  const actaNoExiste = acta.error instanceof ApiError && acta.error.status === 404;

  const liquidar = useMutation({
    mutationFn: (id: string) => apiFetch<Orden>(`/ordenes/${id}/liquidar`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ordenes"] }),
  });

  const adenda = useMutation({
    mutationFn: () =>
      apiFetch(`/ordenes/${enAdenda!.id}/adendas`, {
        method: "POST",
        body: {
          observacion: obs.trim(),
          ...(codigo.trim() ? { ajuste_repuestos: [{ repuesto_codigo: codigo.trim(), delta: Number(delta) }] } : {}),
        },
      }),
    onSuccess: async () => {
      // La adenda puede haber movido stock.
      await Promise.all(["adendas", "repuestos", "movimientos"].map((k) => qc.invalidateQueries({ queryKey: [k] })));
      setEnAdenda(null);
    },
  });

  function abrirAdenda(o: Orden) {
    adenda.reset();
    setErrores({});
    setObs("");
    setCodigo("");
    setDelta("");
    setEnAdenda(o);
  }

  function enviar() {
    const e: Errores = {};
    if (!obs.trim()) e.obs = "La observación es obligatoria";
    if (codigo.trim() || delta.trim()) {
      if (!codigo.trim()) e.codigo = "Indica el código del repuesto";
      if (!DELTA_RE.test(delta.trim())) e.delta = "El ajuste debe ser un entero distinto de 0";
    }
    setErrores(e);
    if (Object.keys(e).length === 0) adenda.mutate();
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">Órdenes sincronizadas</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">Liquidación de órdenes</h1>
          <p className="mt-1 text-sm text-slate-500">Revisión del acta y cierre administrativo por estado.</p>
        </div>
        <div className="w-56">
          <SelectField label="Estado" value={estado} onChange={(e) => setEstado(e.target.value)}>
            <option value="">Todas</option>
            {ESTADOS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </SelectField>
        </div>
      </div>

      {enAdenda && (
        <FormPanel
          title={`Nota de corrección · orden ${enAdenda.id.slice(0, 8)}`}
          onSubmit={enviar}
          onCancel={() => setEnAdenda(null)}
          saving={adenda.isPending}
          error={mensajeDe(adenda.error)}
        >
          <FormField label="Observación" value={obs} onChange={(e) => setObs(e.target.value)} error={errores.obs} />
          <FormField label="Código de repuesto (opcional)" value={codigo} onChange={(e) => setCodigo(e.target.value)} error={errores.codigo} />
          <FormField label="Ajuste de cantidad (+ devuelve, − descuenta)" value={delta} onChange={(e) => setDelta(e.target.value)} inputMode="numeric" error={errores.delta} />

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm sm:col-span-2">
            <h3 className="mb-2 font-semibold text-slate-900">Acta firmada (solo lectura)</h3>
            {acta.isLoading && <p className="text-slate-500">Cargando acta…</p>}
            {actaNoExiste && <p className="text-slate-500">Esta orden está sin acta sincronizada todavía.</p>}
            {acta.error && !actaNoExiste && <p className="text-rose-700">{mensajeDe(acta.error)}</p>}
            {acta.data && (
              <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1">
                <dt className="text-slate-500">Hash</dt>
                <dd className="break-all font-mono text-xs">{acta.data.hash_sha256}</dd>
                <dt className="text-slate-500">Hash anterior</dt>
                <dd className="break-all font-mono text-xs">{acta.data.previous_hash ?? "— (primera acta del equipo)"}</dd>
                <dt className="text-slate-500">GPS</dt>
                <dd>
                  {acta.data.gps_latitud}, {acta.data.gps_longitud}
                </dd>
                <dt className="text-slate-500">Firmada</dt>
                <dd>{fechaHora(acta.data.creado_en)}</dd>
              </dl>
            )}
          </div>

          {(previas.data ?? []).length > 0 && (
            <ul className="text-sm text-slate-600 sm:col-span-2">
              {previas.data!.map((a) => (
                <li key={a.id}>
                  {fechaHora(a.fecha_adenda)} — {a.observacion}
                </li>
              ))}
            </ul>
          )}
        </FormPanel>
      )}

      {liquidar.error && (
        <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-medium text-rose-800">
          {mensajeDe(liquidar.error)}
        </p>
      )}

      <DataTable
        rows={ordenes.data ?? []}
        rowKey={(o) => o.id}
        loading={ordenes.isLoading}
        error={mensajeDe(ordenes.error)}
        actions={(o) => (
          <>
            {o.estado !== "LIQUIDADA" && (
              <button
                type="button"
                className="text-sky-700 hover:underline"
                onClick={() => window.confirm("¿Liquidar la orden? Se consolida la baja contable.") && liquidar.mutate(o.id)}
              >
                Liquidar
              </button>
            )}
            <button type="button" className="text-slate-700 hover:underline" onClick={() => abrirAdenda(o)}>
              Adenda
            </button>
          </>
        )}
        columns={[
          { header: "Orden", cell: (o) => o.id.slice(0, 8) },
          { header: "Equipo", cell: (o) => o.equipo_serie ?? "—" },
          { header: "Intervención", cell: (o) => o.tipo_intervencion },
          { header: "Estado", cell: (o) => <EstadoOrden estado={o.estado} /> },
          { header: "Sincronizada", cell: (o) => fechaHora(o.fecha_sincronizacion) },
        ]}
      />
    </section>
  );
}
