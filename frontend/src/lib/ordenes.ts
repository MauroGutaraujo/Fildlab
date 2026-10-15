// Formateador de presentación: construye un código de orden legible para humanos
// (OT-{NUM}{INICIALES_CLIENTE}{DDMMAA}) sin tocar el UUID real, que sigue siendo
// la clave enviada al backend y mostrada como respaldo para auditoría legal.

export type ContratoMin = { id: number; cliente_ruc: string };
export type ClienteMin = { ruc: string; razon_social: string };
export type OrdenParaFormato = { id: string; contrato_id: number | null; fecha_creacion_cliente: string };

export function razonSocialDeOrden(contratoId: number | null, contratos: ContratoMin[], clientes: ClienteMin[]): string | null {
  const contrato = contratos.find((c) => c.id === contratoId);
  if (!contrato) return null;
  const cliente = clientes.find((c) => c.ruc === contrato.cliente_ruc);
  return cliente?.razon_social ?? null;
}

function siglasDe(razonSocial: string | null): string {
  if (!razonSocial) return "GEN";
  const siglas = razonSocial
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((palabra) => palabra[0]!.toUpperCase())
    .join("")
    .slice(0, 4);
  return siglas || "GEN";
}

function ddmmaa(fechaIso: string): string {
  const f = new Date(fechaIso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(f.getUTCDate())}${p(f.getUTCMonth() + 1)}${String(f.getUTCFullYear()).slice(-2)}`;
}

/** NUM: correlativo de dos dígitos si se indica `indice`; si no, los dos primeros caracteres hex del UUID. */
export function formatearOrdenAmigable(orden: OrdenParaFormato, razonSocial: string | null, indice?: number): string {
  const num = indice !== undefined ? String((indice % 99) + 1).padStart(2, "0") : orden.id.slice(0, 2).toUpperCase();
  return `OT-${num}${siglasDe(razonSocial)}${ddmmaa(orden.fecha_creacion_cliente)}`;
}
