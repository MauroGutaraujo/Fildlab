export function errorTiemposServicio(solicitud?: string, atencion?: string, cierre = new Date().toISOString()): string | null {
  if (!solicitud && !atencion) return null;
  if (!solicitud || !atencion) return "Completa ambas fechas o deja las dos vacías si no tienes esa información";
  const inicio = Date.parse(solicitud), llegada = Date.parse(atencion), fin = Date.parse(cierre);
  if (![inicio, llegada, fin].every(Number.isFinite)) return "Indica fechas de solicitud y atención válidas";
  if (llegada < inicio) return "La primera atención no puede ser anterior a la solicitud";
  if (llegada > fin) return "La primera atención no puede estar en el futuro";
  return null;
}
