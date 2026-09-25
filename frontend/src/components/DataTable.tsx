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
      <div role="alert" className="rounded-2xl border border-red-200 bg-red-50/80 p-4 text-sm font-medium text-red-800 shadow-xs flex items-center gap-2">
        <span className="text-base">⚠️</span>
        <span>{error}</span>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div className="flex flex-col items-center gap-2.5">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="text-xs font-semibold text-slate-400">Cargando registros…</p>
        </div>
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center shadow-xs">
        <span className="text-2xl mb-1 block">📋</span>
        <p className="text-sm font-medium text-slate-500">Sin datos disponibles</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50/80 border-b border-slate-200/80 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <tr>
              {columns.map((c) => (
                <th key={c.header} scope="col" className="px-4 py-3.5">
                  {c.header}
                </th>
              ))}
              {hayAcciones && <th scope="col" className="px-4 py-3.5 text-right font-medium">Acciones</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => (
              <tr key={rowKey(row)} className="hover:bg-blue-50/30 transition-colors">
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
