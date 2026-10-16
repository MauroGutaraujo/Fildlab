import { ReactNode, useState } from "react";

export type Column<T> = { header: string; cell: (row: T) => ReactNode };

type Props<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onEdit?: (row: T) => void;
  canEdit?: (row: T) => boolean;
  actions?: (row: T) => ReactNode;
  loading?: boolean;
  error?: string | null;
  searchable?: boolean;
  searchPlaceholder?: string;
  searchFilter?: (row: T, query: string) => boolean;
  pageSize?: number;
  paginated?: boolean;
};

const TAMANOS_PAGINA = [10, 25, 50];

function coincidePorDefecto<T>(row: T, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  if (typeof row !== "object" || row === null) return false;
  return Object.values(row).some((val) => {
    if (val === null || val === undefined) return false;
    if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
      return String(val).toLowerCase().includes(q);
    }
    return false;
  });
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onEdit,
  canEdit,
  actions,
  loading,
  error,
  searchable = true,
  searchPlaceholder = "Buscar...",
  searchFilter,
  pageSize = 10,
  paginated = true,
}: Props<T>) {
  const hayAcciones = Boolean(onEdit || actions);
  const [query, setQuery] = useState("");
  const [pagina, setPagina] = useState(1);
  const [tam, setTam] = useState(pageSize || 10);

  function buscar(valor: string) {
    setQuery(valor);
    setPagina(1);
  }

  if (error) {
    return (
      <div role="alert" className="flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-800">
        <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3.5m0 3.5h.01M10.29 3.86l-8.09 14A1 1 0 003.09 19h17.82a1 1 0 00.87-1.5l-8.09-14a1 1 0 00-1.74 0z" />
        </svg>
        <span>{error}</span>
      </div>
    );
  }
  if (loading) {
    return (
      <div role="status" aria-live="polite" className="flex items-center justify-center rounded-xl border border-slate-200 bg-white p-8">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-500">Cargando registros…</p>
        </div>
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <svg className="h-8 w-8 mx-auto mb-1.5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-6 4h6M9 5h6a2 2 0 012 2v12a2 2 0 01-2 2H9a2 2 0 01-2-2V7a2 2 0 012-2zm3-2v4" />
        </svg>
        <p className="text-sm font-medium text-slate-600">Sin datos disponibles</p>
      </div>
    );
  }

  const filtradas = query.trim() ? rows.filter((r) => (searchFilter ? searchFilter(r, query) : coincidePorDefecto(r, query))) : rows;
  const sinPaginar = !paginated || pageSize === 0;
  const totalPaginas = sinPaginar ? 1 : Math.max(1, Math.ceil(filtradas.length / tam));
  const paginaActual = Math.min(pagina, totalPaginas);
  const visibles = sinPaginar ? filtradas : filtradas.slice((paginaActual - 1) * tam, paginaActual * tam);

  return (
    <div className="space-y-3">
      {searchable && (
        <div className="relative max-w-sm">
          <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-5.2-5.2m2.2-5.3a7.5 7.5 0 11-15 0 7.5 7.5 0 0115 0z" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => buscar(e.target.value)}
            placeholder={searchPlaceholder}
            aria-label={searchPlaceholder}
            className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-9 text-sm text-slate-700 placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
          />
          {query && (
            <button
              type="button"
              aria-label="Limpiar"
              onClick={() => buscar("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {filtradas.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <p className="text-sm font-medium text-slate-500">No se encontraron resultados para «{query}»</p>
          <button type="button" onClick={() => buscar("")} className="mt-2 text-sm font-semibold text-blue-600 hover:underline cursor-pointer">
            Limpiar búsqueda
          </button>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <tr>
                    {columns.map((c) => (
                      <th key={c.header} scope="col" className="whitespace-nowrap px-4 py-3 text-[11px]">
                        {c.header}
                      </th>
                    ))}
                    {hayAcciones && <th scope="col" className="whitespace-nowrap px-4 py-3 text-right text-[11px] font-medium">Acciones</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {visibles.map((row) => (
                    <tr key={rowKey(row)} className="transition-colors hover:bg-sky-50/60">
                      {columns.map((c) => (
                        <td key={c.header} className="px-4 py-3.5 text-slate-700">
                          {c.cell(row)}
                        </td>
                      ))}
                      {hayAcciones && (
                        <td className="space-x-3 px-4 py-3.5 text-right">
                          {onEdit && (canEdit?.(row) ?? true) && (
                            <button
                              type="button"
                              onClick={() => onEdit(row)}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                            >
                              Editar
                            </button>
                          )}
                          {actions?.(row)}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {!sinPaginar && (
            <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-sm text-slate-600">
              <span>
                Mostrando {(paginaActual - 1) * tam + 1} - {Math.min(paginaActual * tam, filtradas.length)} de {filtradas.length} registros
              </span>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1.5 text-xs">
                  Filas por página
                  <select
                    value={tam}
                    onChange={(e) => {
                      setTam(Number(e.target.value));
                      setPagina(1);
                    }}
                    className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs"
                  >
                    {TAMANOS_PAGINA.map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </label>
                {totalPaginas > 1 && (
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      disabled={paginaActual === 1}
                      onClick={() => setPagina((p) => p - 1)}
                      className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
                    >
                      Anterior
                    </button>
                    {Array.from({ length: totalPaginas }, (_, i) => i + 1).map((n) => (
                      <button
                        type="button"
                        key={n}
                        aria-current={n === paginaActual}
                        onClick={() => setPagina(n)}
                        className={`rounded-lg px-2.5 py-1 text-xs font-medium cursor-pointer ${
                          n === paginaActual ? "bg-blue-600 text-white" : "border border-slate-200 text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                    <button
                      type="button"
                      disabled={paginaActual === totalPaginas}
                      onClick={() => setPagina((p) => p + 1)}
                      className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
                    >
                      Siguiente
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
