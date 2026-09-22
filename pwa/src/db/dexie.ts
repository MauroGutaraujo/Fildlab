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
  tipo: "cliente" | "equipo" | "contrato";
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
  lecturas_agua: LecturasAgua;
  firma_base64: string;
  gps_latitud: number;
  gps_longitud: number;
  repuestos_consumidos: RepuestoConsumido[];
  estado_sync: EstadoSync;
  error_detalle?: string;
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
}

class FildlabDB extends Dexie {
  catalogoLocal!: Table<CatalogoItem, string>;
  ordenesLocal!: Table<OrdenLocal, string>;
  stockMovilLocal!: Table<StockMovilItem, string>;
  sesion!: Table<SesionTurno, string>;

  constructor() {
    super("fildlab-pwa");
    this.version(1).stores({
      catalogoLocal: "id, tipo",
      ordenesLocal: "id, estado_sync, creado_en_local",
      stockMovilLocal: "repuesto_codigo, turno_id",
      sesion: "id",
    });
  }
}

export const db = new FildlabDB();
