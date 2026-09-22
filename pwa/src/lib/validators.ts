// Duplicado + extendido de frontend/src/lib/validators.ts (decisión A del spec de 3.2).
// Reglas espejo del backend (Pydantic). El backend sigue siendo la autoridad.

export const RUC_RE = /^[0-9]{11}$/;

export function errorRuc(ruc: string): string | null {
  return RUC_RE.test(ruc) ? null : "El RUC debe tener exactamente 11 dígitos";
}

const CAMPOS_LECTURA = {
  tds_entrada_ppm: "TDS entrada",
  tds_post_membrana_ppm: "TDS post-membrana",
  tds_producto_final_ppm: "TDS producto final",
  ph: "pH",
  conductividad_us_cm: "Conductividad",
  resistividad_mohm_cm: "Resistividad",
  litros_consumidos_red: "Litros consumidos de red",
  litros_agua_pura: "Litros de agua pura",
} as const;

export type CampoLectura = keyof typeof CAMPOS_LECTURA;
export const CAMPOS_LECTURA_ORDEN = Object.keys(CAMPOS_LECTURA) as CampoLectura[];

/** RN-02: mismos límites que ParametrosNominales/LecturasAgua del backend (no negativos, pH 0-14). */
export function errorLectura(campo: CampoLectura, valor: string): string | null {
  if (valor.trim() === "") return `${CAMPOS_LECTURA[campo]} es obligatorio`;
  const n = Number(valor);
  if (Number.isNaN(n)) return `${CAMPOS_LECTURA[campo]} debe ser un número`;
  if (campo === "ph") {
    return n >= 0 && n <= 14 ? null : "El pH debe estar entre 0 y 14";
  }
  return n >= 0 ? null : `${CAMPOS_LECTURA[campo]} no puede ser negativo`;
}

export function mensajeDe(e: unknown): string | null {
  if (!e) return null;
  return e instanceof Error ? e.message : "Ocurrió un error inesperado";
}
