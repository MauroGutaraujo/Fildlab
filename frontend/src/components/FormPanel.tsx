import { FormEvent, ReactNode, useEffect, useRef } from "react";

type Props = {
  title: string;
  onSubmit: () => void;
  onCancel: () => void;
  saving?: boolean;
  submitLabel?: string;
  error?: string | null;
  children: ReactNode;
};

export function FormPanel({ title, onSubmit, onCancel, saving, submitLabel = "Guardar", error, children }: Props) {
  const ref = useRef<HTMLFormElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, []);
  function enviar(e: FormEvent) {
    e.preventDefault();
    if (!saving) onSubmit();
  }
  return (
    <form ref={ref} onSubmit={enviar} noValidate className="mb-6 space-y-5 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <h2 className="text-base font-bold tracking-tight text-slate-900">{title}</h2>
        <span className="rounded-full border border-blue-100 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800">
          Formulario
        </span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
      {error && (
        <div role="alert" className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-medium text-rose-800">
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3.5m0 3.5h.01M10.29 3.86l-8.09 14A1 1 0 003.09 19h17.82a1 1 0 00.87-1.5l-8.09-14a1 1 0 00-1.74 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? "Guardando…" : submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
