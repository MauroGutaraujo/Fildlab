type Repuesto = { repuesto_codigo: string; cantidad: number };
type Sugerencia = { codigo: string; texto: string };
type Props = {
  codigo: string;
  cantidad: string;
  repuestos: Repuesto[];
  error: string | null;
  sugerencias?: Sugerencia[];
  onCodigoChange: (codigo: string) => void;
  onCantidadChange: (cantidad: string) => void;
  onAgregar: () => void;
};

export function RepuestosSection({ codigo, cantidad, repuestos, error, sugerencias = [], onCodigoChange, onCantidadChange, onAgregar }: Props) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-bold text-slate-900">Repuestos consumidos</h2>
      <p className="mt-1 text-sm text-slate-500">Agrega las piezas utilizadas; el stock móvil se descuenta al confirmar.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_9rem_auto] sm:items-end">
        <label className="block text-sm font-medium text-slate-700">
          Código de repuesto
          <input
            value={codigo}
            onChange={(e) => onCodigoChange(e.target.value)}
            autoComplete="off"
            list="repuestos-disponibles"
            className="mt-1.5 min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-3 text-base text-slate-950 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
          <datalist id="repuestos-disponibles">
            {sugerencias.map((s) => (
              <option key={s.codigo} value={s.codigo}>{s.texto}</option>
            ))}
          </datalist>
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Cantidad consumida
          <input
            value={cantidad}
            onChange={(e) => onCantidadChange(e.target.value)}
            inputMode="numeric"
            className="mt-1.5 min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-3 text-base text-slate-950 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <button
          type="button"
          onClick={onAgregar}
          className="min-h-12 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-900 transition hover:bg-blue-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          Agregar repuesto
        </button>
      </div>
      {error && <p role="alert" className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-800">{error}</p>}
      {repuestos.length > 0 && (
        <ul aria-label="Repuestos agregados" className="mt-4 divide-y divide-slate-100 rounded-lg border border-slate-200">
          {repuestos.map((repuesto, index) => (
            <li key={`${repuesto.repuesto_codigo}-${index}`} className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm">
              <span className="font-medium text-slate-800">{repuesto.repuesto_codigo} × {repuesto.cantidad}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
