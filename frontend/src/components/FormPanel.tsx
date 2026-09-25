import { FormEvent, ReactNode } from "react";

type Props = {
  title: string;
  onSubmit: () => void;
  onCancel: () => void;
  saving?: boolean;
  error?: string | null;
  children: ReactNode;
};

export function FormPanel({ title, onSubmit, onCancel, saving, error, children }: Props) {
  function enviar(e: FormEvent) {
    e.preventDefault();
    if (!saving) onSubmit();
  }
  return (
    <form onSubmit={enviar} noValidate className="mb-6 space-y-4 rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3.5">
        <h2 className="text-base font-bold text-slate-800 tracking-tight">{title}</h2>
        <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full border border-blue-100">
          Formulario
        </span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
      {error && (
        <div role="alert" className="rounded-xl bg-red-50 border border-red-200/80 p-3 text-xs font-semibold text-red-700 flex items-center gap-2">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-xl bg-gradient-to-r from-blue-600 via-blue-600 to-sky-600 hover:from-blue-700 hover:to-sky-700 px-5 py-2.5 text-sm font-semibold text-white shadow-xs hover:shadow active:scale-95 transition-all disabled:opacity-60 cursor-pointer"
        >
          {saving ? "Guardando…" : "Guardar"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-xl border border-slate-300 bg-white hover:bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors cursor-pointer"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
