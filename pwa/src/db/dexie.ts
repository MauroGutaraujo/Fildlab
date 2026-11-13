import Dexie, { type Table } from "dexie";

export type EstadoSync = "borrador" | "pendiente" | "sincronizando" | "sincronizada" | "error";

export interface LecturasAgua {
  tds_entrada_ppm: number;
  tds_post_membrana_ppm: number;
  tds_producto_final_ppm: number;
  ph: number;
  conductividad_us_cm: number;
  resistividad_mohm_cm: number;
  litros_consumidos_red: number;
  litros_agua_pura: number;
}

export interface CatalogoItem {
  id: string;
  tipo: "cliente" | "equipo" | "contrato" | "repuesto";
  datos: unknown;
  actualizado_en: string;
}

export interface RepuestoConsumido {
  repuesto_codigo: string;
  cantidad: number;
}

export interface OrdenLocal {
  id: string;
  contrato_id: number;
  equipo_serie: string;
  tecnico_id: number;
  tipo_intervencion: string;
  fecha_creacion_cliente: string;
  fecha_solicitud?: string;
  fecha_primera_atencion?: string;
  lecturas_agua: LecturasAgua;
  firma_base64: string;
  gps_latitud: number;
  gps_longitud: number;
  repuestos_consumidos: RepuestoConsumido[];
  estado_sync: EstadoSync;
  error_detalle?: string;
  error_status?: number;
  creado_en_local: string;
  intentos_sync: number;
}

export interface StockMovilItem {
  repuesto_codigo: string;
  cantidad_cargada: number;
  cantidad_consumida: number;
  turno_id: string;
}

export interface SesionTurno {
  id: "actual";
  token: string;
  guardado_en: string;
  requiere_renovacion?: boolean;
}

export interface StockTecnicoItem extends StockMovilItem {
  tecnico_id: number;
}

export interface BorradorOrden {
  id: string;
  revision: number;
  fecha_solicitud?: string;
  fecha_primera_atencion?: string;
  tecnico_id: number;
  equipo_serie: string;
  contrato_id: number;
  tipo_intervencion: "PREVENTIVO" | "CORRECTIVO";
  lecturas: Record<keyof LecturasAgua, string>;
  firma_base64: string | null;
  gps_latitud: number | null;
  gps_longitud: number | null;
  repuestos_consumidos: RepuestoConsumido[];
  creado_en_local: string;
}

class FildlabDB extends Dexie {
  catalogoLocal!: Table<CatalogoItem, string>;
  ordenesLocal!: Table<OrdenLocal, string>;
  stockMovilLocal!: Table<StockMovilItem, string>;
  sesion!: Table<SesionTurno, string>;
  stockPorTecnico!: Table<StockTecnicoItem, [number, string]>;
  borradoresOrden!: Table<BorradorOrden, [number, string]>;

  constructor() {
    super("fildlab-pwa");
    this.version(1).stores({
      catalogoLocal: "id, tipo",
      ordenesLocal: "id, estado_sync, creado_en_local",
      stockMovilLocal: "repuesto_codigo, turno_id",
      sesion: "id",
    });
    // El stock v1 no tiene propietario: se conserva para reconciliarlo, nunca
    // se asigna automáticamente al siguiente usuario del dispositivo.
    this.version(2).stores({
      ordenesLocal: "id, estado_sync, creado_en_local, tecnico_id",
      stockPorTecnico: "[tecnico_id+repuesto_codigo], tecnico_id",
      borradoresOrden: "[tecnico_id+equipo_serie], &id, tecnico_id",
    });
  }
}

export const db = new FildlabDB();
