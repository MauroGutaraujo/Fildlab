import { FormEvent, useState } from "react";
import { cargarStockTurno } from "../../db/stock";

export function StockMovil() {
  const [codigo, setCodigo] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [turnoId] = useState(() => crypto.randomUUID());

  async function cargar(e: FormEvent) {
    e.preventDefault();
    if (!codigo.trim() || !cantidad) return;
    await cargarStockTurno([{ repuesto_codigo: codigo.trim(), cantidad: Number(cantidad) }], turnoId);
    setCodigo("");
    setCantidad("");
  }

  return (
    <section className="space-y-4 p-4 pb-28">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Inventario técnico</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Stock móvil de turno</h1>
        <p className="mt-1 text-sm text-slate-600">Registra los repuestos disponibles antes de iniciar la ruta.</p>
      </header>
      <form onSubmit={cargar} className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="block text-sm font-medium text-slate-700">
          Código de repuesto
          <input
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            className="mt-1.5 min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-3 text-base text-slate-950 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Cantidad cargada
          <input
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
            inputMode="numeric"
            className="mt-1.5 min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-3 text-base text-slate-950 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <button type="submit" className="min-h-12 w-full rounded-lg bg-blue-800 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700">
          Cargar
        </button>
      </form>
    </section>
  );
}
