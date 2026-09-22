import { InputHTMLAttributes, useId } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string | null };

export function FormField({ label, error, ...input }: Props) {
  const id = useId();
  return (
    <div className="text-sm">
      <label htmlFor={id} className="block font-medium">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-err` : undefined}
        className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
        {...input}
      />
      {error && (
        <p id={`${id}-err`} className="mt-1 text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
