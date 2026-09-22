import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { DataTable } from "../../components/DataTable";
import { FormField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { centavos, errorCantidad, errorCosto, errorRuc, fechaHora, mensajeDe } from "../../lib/validators";

type Venta = {
  id: number;
  cliente_ruc: string;
  total_soles: string;
  fecha: string;
  items: { repuesto_codigo: string; cantidad: number; precio_unitario_soles: string }[];
};
type Item = { codigo: string; cantidad: string; precio: string };
type ErrItem = Partial<Record<keyof Item, string>>;

const vacio = (): Item => ({ codigo: "", cantidad: "", precio: "" });
const soles = (c: number) => (c / 100).toFixed(2);

export function VentasPage() {
  const puedeEscribir = useAuth().user?.rol === "GERENCIA";
  const qc = useQueryClient();
  const { data = [], isLoading, error } = useQuery({ queryKey: ["ventas"], queryFn: () => apiFetch<Venta[]>("/ventas") });

  const [abierto, setAbierto] = useState(false);
  const [ruc, setRuc] = useState("");
  const [items, setItems] = useState<Item[]>([vacio()]);
  const [errRuc, setErrRuc] = useState<string | null>(null);
  const [errItems, setErrItems] = useState<ErrItem[]>([]);

  const crear = useMutation({
    mutationFn: () =>
      apiFetch<Venta>("/ventas", {
        method: "POST",
        body: {
          cliente_ruc: ruc,
          items: items.map((i) => ({
            repuesto_codigo: i.codigo.trim(),
            cantidad: Number(i.cantidad),
            precio_unitario_soles: i.precio.trim(),
          })),
        },
      }),
    onSuccess: async () => {
      // El stock cambió: refrescar también inventario.
      await Promise.all(["ventas", "repuestos", "movimientos"].map((k) => qc.invalidateQueries({ queryKey: [k] })));
      setAbierto(false);
    },
  });

  function abrir() {
    crear.reset();
    setRuc("");
    setItems([vacio()]);
    setErrRuc(null);
    setErrItems([]);
    setAbierto(true);
  }

  const cambiar = (n: number, campo: keyof Item, valor: string) =>
    setItems((prev) => prev.map((it, i) => (i === n ? { ...it, [campo]: valor } : it)));

  const total = items.reduce((s, i) => (errorCantidad(i.cantidad) || errorCosto(i.precio, "precio") ? s : s + Number(i.cantidad) * centavos(i.precio)), 0);

  function enviar() {
    const r = errorRuc(ruc);
    const ei: ErrItem[] = items.map((i) => {
      const e: ErrItem = {};
      if (!i.codigo.trim()) e.codigo = "El código es obligatorio";
      const c = errorCantidad(i.cantidad);
      if (c) e.cantidad = c;
      const p = errorCosto(i.precio, "precio");
      if (p) e.precio = p;
      return e;
    });
    setErrRuc(r);
    setErrItems(ei);
    if (!r && ei.every((e) => Object.keys(e).length === 0)) crear.mutate();
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Ventas de repuestos</h1>
        {puedeEscribir && !abierto && (
          <button type="button" onClick={abrir} className="rounded bg-sky-700 px-4 py-2 text-white">
            Nueva venta
          </button>
        )}
      </div>

      {abierto && (
        <FormPanel title="Nueva venta" onSubmit={enviar} onCancel={() => setAbierto(false)} saving={crear.isPending} error={mensajeDe(crear.error)}>
          <FormField label="RUC del cliente" value={ruc} onChange={(e) => setRuc(e.target.value)} inputMode="numeric" error={errRuc} />
          <div className="space-y-3 sm:col-span-2">
            {items.map((it, n) => (
              <div key={n} className="grid items-start gap-2 sm:grid-cols-[2fr_1fr_1fr_auto]">
                <FormField label={`Código de repuesto ${n + 1}`} value={it.codigo} onChange={(e) => cambiar(n, "codigo", e.target.value)} error={errItems[n]?.codigo} />
                <FormField label={`Cantidad ${n + 1}`} value={it.cantidad} onChange={(e) => cambiar(n, "cantidad", e.target.value)} inputMode="numeric" error={errItems[n]?.cantidad} />
                <FormField label={`Precio unitario (S/) ${n + 1}`} value={it.precio} onChange={(e) => cambiar(n, "precio", e.target.value)} inputMode="decimal" error={errItems[n]?.precio} />
                {items.length > 1 && (
                  <button type="button" aria-label={`Quitar ítem ${n + 1}`} onClick={() => setItems((p) => p.filter((_, i) => i !== n))} className="mt-6 text-red-700">
                    Quitar
                  </button>
                )}
              </div>
            ))}
            <button type="button" onClick={() => setItems((p) => [...p, vacio()])} className="text-sky-700 hover:underline">
              Agregar ítem
            </button>
            <p className="font-semibold">Total: S/ {soles(total)}</p>
          </div>
        </FormPanel>
      )}

      <DataTable
        rows={data}
        rowKey={(v) => v.id}
        loading={isLoading}
        error={mensajeDe(error)}
        columns={[
          { header: "Fecha", cell: (v) => fechaHora(v.fecha) },
          { header: "Cliente (RUC)", cell: (v) => v.cliente_ruc },
          { header: "Ítems", cell: (v) => v.items.length },
          { header: "Total", cell: (v) => `S/ ${v.total_soles}` },
        ]}
      />
    </section>
  );
}
