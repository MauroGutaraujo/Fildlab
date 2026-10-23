import { FormEvent, useEffect, useState } from "react";
import { cargarStockTurno } from "../../db/stock";
import { db } from "../../db/dexie";

export function StockMovil({ tecnicoId }: { tecnicoId: number }) {
  const [codigo, setCodigo] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [turnoId] = useState(() => crypto.randomUUID());

  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [hayStockAnterior, setHayStockAnterior] = useState(false);

  useEffect(() => {
    let activo = true;
    db.stockMovilLocal.count().then((n) => { if (activo) setHayStockAnterior(n > 0); })
      .catch(() => { if (activo) setError("No se pudo consultar el stock anterior"); });
    return () => { activo = false; };
  }, []);

  async function cargar(e: FormEvent) {
    e.preventDefault();
    if (guardando) return;
    const unidades = Number(cantidad);
    if (!codigo.trim() || !Number.isSafeInteger(unidades) || unidades <= 0) {
      setError("Indica un código y una cantidad entera positiva"); return;
    }
    setError(null); setGuardando(true);
    try {
      await cargarStockTurno([{ repuesto_codigo: codigo.trim(), cantidad: unidades }], turnoId, tecnicoId);
      setCodigo(""); setCantidad("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar la carga. Intenta de nuevo");
    } finally { setGuardando(false); }
  }

  return (
    <section className="space-y-4 p-4 pb-28">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Inventario técnico</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Stock móvil de turno</h1>
        <p className="mt-1 text-sm text-slate-600">Registra los repuestos disponibles antes de iniciar la ruta.</p>
      </header>
      {hayStockAnterior && <p className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">Hay stock anterior sin técnico asignado. Se conserva en este dispositivo; coordina con Gerencia la revisión del saldo antes de registrar tu carga.</p>}
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
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
        <button type="submit" disabled={guardando} className="min-h-12 w-full rounded-lg bg-blue-800 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700">
          {guardando ? "Guardando…" : "Cargar"}
        </button>
      </form>
    </section>
  );
}
