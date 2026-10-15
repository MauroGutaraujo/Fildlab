import { ReactNode } from "react";

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
};

export function DataTable<T>({ columns, rows, rowKey, onEdit, canEdit, actions, loading, error }: Props<T>) {
  const hayAcciones = Boolean(onEdit || actions);
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

  return (
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
            {rows.map((row) => (
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
  );
}
