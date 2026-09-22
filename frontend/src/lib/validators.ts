// Reglas espejo del backend (Pydantic). El backend sigue siendo la autoridad.

export const RUC_RE = /^[0-9]{11}$/;
const DECIMAL_2 = /^[0-9]{1,8}(\.[0-9]{1,2})?$/;

export function errorRuc(ruc: string): string | null {
  return RUC_RE.test(ruc) ? null : "El RUC debe tener exactamente 11 dígitos";
}

export function errorMonto(monto: string): string | null {
  const m = monto.trim();
  return DECIMAL_2.test(m) && Number(m) > 0 ? null : "El monto debe ser mayor que 0 y tener máximo 2 decimales";
}

export function errorSla(horas: string): string | null {
  return /^[1-9][0-9]{0,3}$/.test(horas.trim()) ? null : "El SLA debe ser un entero mayor que 0";
}

export function errorCosto(v: string, campo = "costo"): string | null {
  return DECIMAL_2.test(v.trim()) ? null : `El ${campo} debe ser un número mayor o igual a 0 (máx. 2 decimales)`;
}

export function errorCantidad(v: string): string | null {
  return /^[1-9][0-9]*$/.test(v.trim()) ? null : "La cantidad debe ser un entero mayor que 0";
}

export function centavos(v: string): number {
  return DECIMAL_2.test(v.trim()) ? Math.round(Number(v.trim()) * 100) : 0;
}

export function hoyISO(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function mensajeDe(e: unknown): string | null {
  if (!e) return null;
  return e instanceof Error ? e.message : "Ocurrió un error inesperado";
}

export function fechaHora(iso: string): string {
  return new Date(iso).toLocaleString("es-PE", { dateStyle: "short", timeStyle: "short" });
}
