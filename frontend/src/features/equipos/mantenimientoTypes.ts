export type Componente = {
  id: string; equipo_serie: string; nombre: string;
  tipo_componente: "MEMBRANA" | "FILTRO" | "RESINA" | "OTRO";
  fecha_instalacion: string | null; fabricante_modelo: string | null;
  creado_por_id: number; creado_en: string; ciclo_actual_desde: string | null;
  revision: number; anulado_en: string | null;
};
export const TRABAJOS = {
  INSPECCION: "Inspección", LIMPIEZA: "Limpieza", REPARACION_PARCIAL: "Reparación parcial", SUSTITUCION: "Sustitución",
} as const;
export type Trabajo = keyof typeof TRABAJOS;
export type Intervencion = {
  id: string; componente_id: string; orden_id: string; acta_hash: string; tipo: Trabajo;
  fecha_efectiva: string; observacion: string; registrado_por_id: number;
  registrado_por_nombre: string; registrado_en: string;
  anulacion: { id: string; motivo: string; registrado_por_id: number; registrado_en: string } | null;
};
export type OrdenFirmada = { id: string; tipo_intervencion: string; fecha_creacion_cliente: string };
export type CambioComponente = {
  solicitud_id: string; componente_id: string; accion: "CORREGIR" | "ANULAR_ALTA" | "RESTABLECER_ALTA";
  revision_anterior: number; revision_nueva: number; antes: Record<string, unknown>; despues: Record<string, unknown>;
  solicitud: Record<string, unknown>; motivo: string; registrado_por_id: number; registrado_en: string;
};

export function fechaLima(fecha = new Date()): string {
  const partes = new Intl.DateTimeFormat("en", { timeZone: "America/Lima", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(fecha);
  const valor = (tipo: string) => partes.find((p) => p.type === tipo)!.value;
  return `${valor("year")}-${valor("month")}-${valor("day")}`;
}

export function horaLima(iso: string): string {
  return new Intl.DateTimeFormat("es-PE", { timeZone: "America/Lima", dateStyle: "short", timeStyle: "short" }).format(new Date(iso));
}
