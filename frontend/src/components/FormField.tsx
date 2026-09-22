import { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes, useId } from "react";

const CAMPO = "mt-1 w-full rounded border border-slate-300 px-3 py-2";

function Envoltorio({ id, label, error, children }: { id: string; label: string; error?: string | null; children: ReactNode }) {
  return (
    <div className="text-sm">
      <label htmlFor={id} className="block font-medium">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-err`} className="mt-1 text-red-700">
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
