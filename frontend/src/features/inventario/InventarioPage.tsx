import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { DataTable } from "../../components/DataTable";
import { FormField, SelectField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { errorCantidad, errorCosto, fechaHora, mensajeDe } from "../../lib/validators";
import { formatearOrdenAmigable, razonSocialDeOrden, type ClienteMin, type ContratoMin } from "../../lib/ordenes";

type Repuesto = { codigo: string; descripcion: string; stock_almacen_central: number; costo_unitario_soles: string };
type Movimiento = { id: number; repuesto_codigo: string; tipo: string; cantidad: number; creado_en: string };
type OrdenMin = { id: string; contrato_id: number | null; fecha_creacion_cliente: string };

const TIPOS_MOV = ["ENTRADA", "SALIDA_ORDEN", "AJUSTE_ENTRADA", "AJUSTE_SALIDA"] as const;
type TipoMov = (typeof TIPOS_MOV)[number];
const SUMAN = new Set(["ENTRADA", "AJUSTE_ENTRADA"]);

type Panel = null | "repuesto" | "movimiento";
type Errores = Partial<Record<"codigo" | "descripcion" | "costo" | "repuesto" | "cantidad" | "orden", string>>;

function EstadoStock({ cantidad }: { cantidad: number }) {
  const estado = cantidad === 0
    ? { texto: "Agotado", color: "border-rose-200 bg-rose-50 text-rose-800", punto: "bg-rose-500" }
    : cantidad <= 5
      ? { texto: "Stock bajo", color: "border-amber-200 bg-amber-50 text-amber-800", punto: "bg-amber-500" }
      : cantidad > 10
        ? { texto: "Saludable", color: "border-emerald-200 bg-emerald-50 text-emerald-800", punto: "bg-emerald-500" }
        : { texto: "Stock limitado", color: "border-slate-200 bg-slate-50 text-slate-700", punto: "bg-slate-400" };
  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${estado.color}`}><span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${estado.punto}`} />{estado.texto}<span className="font-normal">· {cantidad}</span></span>;
}

function soles(valor: string) {
  const numero = Number(valor);
  return `S/. ${Number.isFinite(numero) ? numero.toFixed(2) : "0.00"}`;
}

export function InventarioPage() {
  const puedeEscribir = useAuth().user?.rol === "GERENCIA";
  const qc = useQueryClient();
  const repuestos = useQuery({ queryKey: ["repuestos"], queryFn: () => apiFetch<Repuesto[]>("/repuestos") });
  const movimientos = useQuery({ queryKey: ["movimientos"], queryFn: () => apiFetch<Movimiento[]>("/inventario/movimientos") });
  const ordenes = useQuery({ queryKey: ["ordenes"], queryFn: () => apiFetch<OrdenMin[]>("/ordenes") });
  const contratos = useQuery({ queryKey: ["contratos"], queryFn: () => apiFetch<ContratoMin[]>("/contratos") });
  const clientes = useQuery({ queryKey: ["clientes"], queryFn: () => apiFetch<ClienteMin[]>("/clientes") });

  const [panel, setPanel] = useState<Panel>(null);
  const [codigo, setCodigo] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [costo, setCosto] = useState("");
  const [repuesto, setRepuesto] = useState("");
  const [tipo, setTipo] = useState<TipoMov>("ENTRADA");
  const [cantidad, setCantidad] = useState("");
  const [orden, setOrden] = useState("");
  const [errores, setErrores] = useState<Errores>({});

  const refrescar = () => Promise.all([qc.invalidateQueries({ queryKey: ["repuestos"] }), qc.invalidateQueries({ queryKey: ["movimientos"] })]);

  const crearRepuesto = useMutation({
    mutationFn: () =>
      apiFetch<Repuesto>("/repuestos", {
        method: "POST",
        body: { codigo: codigo.trim(), descripcion: descripcion.trim(), costo_unitario_soles: costo.trim() },
      }),
    onSuccess: async () => {
      await refrescar();
      setPanel(null);
    },
  });

  const registrar = useMutation({
    mutationFn: () =>
      apiFetch<Movimiento>("/inventario/movimientos", {
        method: "POST",
        body: {
          repuesto_codigo: repuesto,
          tipo,
          cantidad: Number(cantidad),
          ...(tipo === "SALIDA_ORDEN" ? { orden_id: orden.trim() } : {}),
        },
      }),
    onSuccess: async () => {
      await refrescar();
      setPanel(null);
    },
  });

  function abrir(p: Exclude<Panel, null>) {
    crearRepuesto.reset();
    registrar.reset();
    setErrores({});
    setCodigo("");
    setDescripcion("");
    setCosto("");
    setRepuesto("");
    setTipo("ENTRADA");
    setCantidad("");
    setOrden("");
    setPanel(p);
  }

  function enviarRepuesto() {
    const e: Errores = {};
    if (!codigo.trim()) e.codigo = "El código es obligatorio";
    else if (codigo.trim().length > 30) e.codigo = "El código admite máximo 30 caracteres";
    if (!descripcion.trim()) e.descripcion = "La descripción es obligatoria";
    const c = errorCosto(costo);
    if (c) e.costo = c;
    setErrores(e);
    if (Object.keys(e).length === 0) crearRepuesto.mutate();
  }

  function enviarMovimiento() {
    const e: Errores = {};
    if (!repuesto) e.repuesto = "Elige un repuesto";
    const c = errorCantidad(cantidad);
    if (c) e.cantidad = c;
    if (tipo === "SALIDA_ORDEN" && !orden.trim()) e.orden = "Las salidas por orden requieren elegir la orden";
    setErrores(e);
    if (Object.keys(e).length === 0) registrar.mutate();
  }

  const lista = repuestos.data ?? [];

  function opcionDeOrden(o: OrdenMin, indice: number): string {
    const razon = razonSocialDeOrden(o.contrato_id, contratos.data ?? [], clientes.data ?? []);
    const codigo = formatearOrdenAmigable(o, razon, indice);
    const fecha = new Date(o.fecha_creacion_cliente).toLocaleDateString("es-PE", { timeZone: "UTC" });
    return `${codigo} • ${razon ?? "Sin cliente"} (${fecha})`;
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">Repuestos y disponibilidad</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">Inventario · almacén central</h1>
          <p className="mt-1 text-sm text-slate-500">Niveles de stock y movimientos recientes.</p>
        </div>
        {puedeEscribir && panel === null && (
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => abrir("repuesto")} className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
              Nuevo repuesto
            </button>
            <button type="button" onClick={() => abrir("movimiento")} className="rounded-lg border border-blue-200 bg-white px-4 py-2.5 text-sm font-semibold text-blue-800 transition hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
              Registrar movimiento
            </button>
          </div>
        )}
      </div>

      {panel === "repuesto" && (
        <FormPanel title="Nuevo repuesto" onSubmit={enviarRepuesto} onCancel={() => setPanel(null)} saving={crearRepuesto.isPending} error={mensajeDe(crearRepuesto.error)}>
          <FormField label="Código" value={codigo} onChange={(e) => setCodigo(e.target.value)} error={errores.codigo} />
          <FormField label="Descripción" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} error={errores.descripcion} />
          <FormField label="Costo unitario (S/)" value={costo} onChange={(e) => setCosto(e.target.value)} inputMode="decimal" error={errores.costo} />
        </FormPanel>
      )}

      {panel === "movimiento" && (
        <FormPanel title="Registrar movimiento" onSubmit={enviarMovimiento} onCancel={() => setPanel(null)} saving={registrar.isPending} error={mensajeDe(registrar.error)}>
          <SelectField label="Repuesto" value={repuesto} onChange={(e) => setRepuesto(e.target.value)} error={errores.repuesto}>
            <option value="">Selecciona…</option>
            {lista.map((r) => (
              <option key={r.codigo} value={r.codigo}>
                {r.codigo}
              </option>
            ))}
          </SelectField>
          <SelectField label="Tipo de movimiento" value={tipo} onChange={(e) => setTipo(e.target.value as TipoMov)}>
            {TIPOS_MOV.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </SelectField>
          <FormField label="Cantidad" value={cantidad} onChange={(e) => setCantidad(e.target.value)} inputMode="numeric" error={errores.cantidad} />
          {tipo === "SALIDA_ORDEN" && (
            <SelectField label="Orden" value={orden} onChange={(e) => setOrden(e.target.value)} error={errores.orden}>
              <option value="">Selecciona…</option>
              {(ordenes.data ?? []).map((o, i) => (
                <option key={o.id} value={o.id}>
                  {opcionDeOrden(o, i)}
                </option>
              ))}
            </SelectField>
          )}
        </FormPanel>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 bg-slate-50/70 px-4 py-3.5 sm:px-5">
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">Catálogo de repuestos</h2>
          <p className="mt-0.5 text-sm text-slate-500">Existencias y costo unitario del almacén central.</p>
        </div>
        <DataTable
          rows={lista}
          rowKey={(r) => r.codigo}
          loading={repuestos.isLoading}
          error={mensajeDe(repuestos.error)}
          columns={[
            { header: "Código", cell: (r) => r.codigo },
            { header: "Descripción", cell: (r) => r.descripcion },
            { header: "Stock central", cell: (r) => <EstadoStock cantidad={r.stock_almacen_central} /> },
            { header: "Costo unitario", cell: (r) => <span className="font-medium tabular-nums text-slate-800">{soles(r.costo_unitario_soles)}</span> },
          ]}
        />
      </div>

      <div>
        <div className="mb-3">
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">Historial de entradas y salidas</h2>
          <p className="mt-0.5 text-sm text-slate-500">Movimientos recientes del inventario.</p>
        </div>
        <DataTable
          rows={(movimientos.data ?? []).slice(0, 20)}
          rowKey={(m) => m.id}
          loading={movimientos.isLoading}
          error={mensajeDe(movimientos.error)}
          columns={[
            { header: "Fecha", cell: (m) => fechaHora(m.creado_en) },
            { header: "Repuesto", cell: (m) => m.repuesto_codigo },
            { header: "Tipo", cell: (m) => m.tipo },
            { header: "Cantidad", cell: (m) => `${SUMAN.has(m.tipo) ? "+" : "−"}${m.cantidad}` },
          ]}
        />
      </div>
    </section>
  );
}
