import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { DataTable } from "../../components/DataTable";
import { FormField, SelectField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { errorCantidad, errorCosto, fechaHora, mensajeDe } from "../../lib/validators";

type Repuesto = { codigo: string; descripcion: string; stock_almacen_central: number; costo_unitario_soles: string };
type Movimiento = { id: number; repuesto_codigo: string; tipo: string; cantidad: number; creado_en: string };

const TIPOS_MOV = ["ENTRADA", "SALIDA_ORDEN", "AJUSTE_ENTRADA", "AJUSTE_SALIDA"] as const;
type TipoMov = (typeof TIPOS_MOV)[number];
const SUMAN = new Set(["ENTRADA", "AJUSTE_ENTRADA"]);
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type Panel = null | "repuesto" | "movimiento";
type Errores = Partial<Record<"codigo" | "descripcion" | "costo" | "repuesto" | "cantidad" | "orden", string>>;

export function InventarioPage() {
  const puedeEscribir = useAuth().user?.rol === "GERENCIA";
  const qc = useQueryClient();
  const repuestos = useQuery({ queryKey: ["repuestos"], queryFn: () => apiFetch<Repuesto[]>("/repuestos") });
  const movimientos = useQuery({ queryKey: ["movimientos"], queryFn: () => apiFetch<Movimiento[]>("/inventario/movimientos") });

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
    if (tipo === "SALIDA_ORDEN" && !UUID_RE.test(orden.trim())) e.orden = "Las salidas por orden requieren el UUID de la orden";
    setErrores(e);
    if (Object.keys(e).length === 0) registrar.mutate();
  }

  const lista = repuestos.data ?? [];

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Inventario · almacén central</h1>
        {puedeEscribir && panel === null && (
          <div className="flex gap-2">
            <button type="button" onClick={() => abrir("repuesto")} className="rounded bg-sky-700 px-4 py-2 text-white">
              Nuevo repuesto
            </button>
            <button type="button" onClick={() => abrir("movimiento")} className="rounded border border-sky-700 px-4 py-2 text-sky-700">
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
          {tipo === "SALIDA_ORDEN" && <FormField label="Orden (UUID)" value={orden} onChange={(e) => setOrden(e.target.value)} error={errores.orden} />}
        </FormPanel>
      )}

      <DataTable
        rows={lista}
        rowKey={(r) => r.codigo}
        loading={repuestos.isLoading}
        error={mensajeDe(repuestos.error)}
        columns={[
          { header: "Código", cell: (r) => r.codigo },
          { header: "Descripción", cell: (r) => r.descripcion },
          { header: "Stock central", cell: (r) => r.stock_almacen_central },
          { header: "Costo unitario", cell: (r) => `S/ ${r.costo_unitario_soles}` },
        ]}
      />

      <div>
        <h2 className="mb-2 font-semibold">Movimientos recientes</h2>
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
