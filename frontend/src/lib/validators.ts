// Reglas espejo del backend (Pydantic). El backend sigue siendo la autoridad.

export const RUC_RE = /^[0-9]{11}$/;

export function errorRuc(ruc: string): string | null {
  return RUC_RE.test(ruc) ? null : "El RUC debe tener exactamente 11 dígitos";
}

export function errorMonto(monto: string): string | null {
  const m = monto.trim();
  return /^[0-9]{1,8}(\.[0-9]{1,2})?$/.test(m) && Number(m) > 0
    ? null
    : "El monto debe ser mayor que 0 y tener máximo 2 decimales";
}

export function errorSla(horas: string): string | null {
  return /^[1-9][0-9]{0,3}$/.test(horas.trim()) ? null : "El SLA debe ser un entero mayor que 0";
}

export function mensajeDe(e: unknown): string | null {
  if (!e) return null;
  return e instanceof Error ? e.message : "Ocurrió un error inesperado";
}
