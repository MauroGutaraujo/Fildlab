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
    <form onSubmit={enviar} noValidate className="mb-4 space-y-3 rounded border border-slate-200 bg-white p-4">
      <h2 className="font-semibold">{title}</h2>
      <div className="grid gap-3 sm:grid-cols-2">{children}</div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={saving} className="rounded bg-sky-700 px-4 py-2 text-white disabled:opacity-60">
          {saving ? "Guardando…" : "Guardar"}
        </button>
        <button type="button" onClick={onCancel} className="rounded border border-slate-300 px-4 py-2">
          Cancelar
        </button>
      </div>
    </form>
  );
}
