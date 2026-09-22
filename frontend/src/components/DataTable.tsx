import { ReactNode } from "react";

export type Column<T> = { header: string; cell: (row: T) => ReactNode };

type Props<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onEdit?: (row: T) => void;
  loading?: boolean;
  error?: string | null;
};

export function DataTable<T>({ columns, rows, rowKey, onEdit, loading, error }: Props<T>) {
  if (error) {
    return (
      <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-red-800">
        {error}
      </p>
    );
  }
  if (loading) return <p className="p-3 text-slate-500">Cargando…</p>;
  if (rows.length === 0) return <p className="p-3 text-slate-500">Sin datos disponibles</p>;

  return (
    <div className="overflow-x-auto rounded border border-slate-200 bg-white">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-100 text-slate-600">
          <tr>
            {columns.map((c) => (
              <th key={c.header} scope="col" className="px-3 py-2 font-medium">
                {c.header}
              </th>
            ))}
            {onEdit && <th scope="col" className="px-3 py-2" />}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-t border-slate-100">
              {columns.map((c) => (
                <td key={c.header} className="px-3 py-2">
                  {c.cell(row)}
                </td>
              ))}
              {onEdit && (
                <td className="px-3 py-2 text-right">
                  <button type="button" onClick={() => onEdit(row)} className="text-sky-700 hover:underline">
                    Editar
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
