import { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes, useId } from "react";

const CAMPO = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

function Envoltorio({ id, label, error, children }: { id: string; label: string; error?: string | null; children: ReactNode }) {
  return (
    <div className="text-sm">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-err`} className="mt-1 text-sm text-rose-700">
          {error}
        </p>
      )}
    </div>
  );
}

type Comun = { label: string; error?: string | null };

export function FormField({ label, error, ...input }: Comun & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <Envoltorio id={id} label={label} error={error}>
      <input id={id} aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-err` : undefined} className={CAMPO} {...input} />
    </Envoltorio>
  );
}

export function SelectField({ label, error, children, ...select }: Comun & SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId();
  return (
    <Envoltorio id={id} label={label} error={error}>
      <select id={id} aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-err` : undefined} className={CAMPO} {...select}>
        {children}
      </select>
    </Envoltorio>
  );
}

export function TextAreaField({ label, error, ...area }: Comun & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <Envoltorio id={id} label={label} error={error}>
      <textarea id={id} aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-err` : undefined} className={CAMPO} {...area} />
    </Envoltorio>
  );
}
