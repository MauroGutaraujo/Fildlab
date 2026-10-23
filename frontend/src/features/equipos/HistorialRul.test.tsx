import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderWithProviders } from "../../test/utils";
import { HistorialRul, EjecucionesRul } from "./HistorialRul";

const base="/api/v1/equipos/EQ-1/historial-rul";
const fila={id:"r1",equipo_serie:"EQ-1",ejecucion_id:"run-1",origen:"BATCH",uso:"HISTORICO_NO_VIGENTE",
  calculado_en:"2026-10-22T15:00:00Z",fecha_evaluacion:"2026-10-22",fecha_referencia:"2026-01-01",
  tipo_referencia:"FILTRO",vence_en:"2026-10-24T15:00:00Z",version_calculo:"COX_INSTALACION_V3",
  version_dataset:"WEIBULL_CENSURA_V2",dataset_sha256:"a".repeat(64),modelo_sha256:"b".repeat(64),politica_alerta:"RUL_30_90_V1",
  dias_vida_util_remanente:100,nivel_alerta:"VERDE",motivo_no_estimable:null};

describe("historial de IA",()=>{
  it("muestra datos originales como históricos, pagina y cierra",async()=>{
    mockApi([{path:`${base}?limit=20&offset=0`,body:{items:[fila],total:21,limit:20,offset:0}},
      {path:`${base}?limit=20&offset=20`,body:{items:[{...fila,id:"r2",dias_vida_util_remanente:null,motivo_no_estimable:"MODELO_INESTABLE"}],total:21,limit:20,offset:20}}]);
    renderWithProviders(<HistorialRul serie="EQ-1" onCerrar={()=>{}}/>);
    expect(await screen.findByText(/100 días registrados/i)).toBeInTheDocument();
    expect(screen.getByText(/no representan una recomendación vigente/i)).toBeInTheDocument();
    expect(screen.queryByText(/prioridad experimental baja/i)).not.toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Modelo SHA256: ${"b".repeat(64)}`))).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button",{name:"Siguiente"}));
    expect(await screen.findByText(/MODELO_INESTABLE/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button",{name:"Anterior"}));
    expect(await screen.findByText(/100 días registrados/i)).toBeInTheDocument();
  });

  it("fallo de red permite reintentar sin mostrar datos inventados",async()=>{
    const rutas: {path:string;status:number;body:unknown}[]=[{path:`${base}?limit=20&offset=0`,status:503,body:{detail:"No disponible"}}];
    mockApi(rutas); renderWithProviders(<HistorialRul serie="EQ-1" onCerrar={()=>{}}/>);
    expect(await screen.findByRole("alert")).toHaveTextContent("No disponible");
    rutas[0]={path:`${base}?limit=20&offset=0`,status:200,body:{items:[],total:0}};
    await userEvent.click(screen.getByRole("button",{name:/reintentar historial/i}));
    expect(await screen.findByText(/sin cálculos históricos/i)).toBeInTheDocument();
  });

  it("gerencia ve ejecuciones fallidas con fecha y resultado sin cierre explícito",async()=>{
    mockApi([{path:"/api/v1/equipos/ejecuciones-rul?limit=5&offset=0",body:{total:1,items:[{
      id:"run-1",iniciado_en:"2026-10-22T15:00:00Z",finalizado_en:null,estado:"EN_CURSO",error_codigo:null,
      total:0,estimadas:0,abstenciones:0,version_calculo:"COX_INSTALACION_V3",vigencia_horas:48,
    }]}}]);
    renderWithProviders(<EjecucionesRul/>);
    expect(await screen.findByText(/sin cierre confirmado/i)).toBeInTheDocument();
    expect(screen.queryByText(/completada/i)).not.toBeInTheDocument();
  });
});
