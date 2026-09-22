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
    <section className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Stock móvil de turno</h1>
      <form onSubmit={cargar} className="space-y-3">
        <label className="block text-sm">
          Código de repuesto
          <input
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          Cantidad cargada
          <input
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
            inputMode="numeric"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        <button type="submit" className="rounded bg-sky-700 px-4 py-2 text-white">
          Cargar
        </button>
      </form>
    </section>
  );
}
