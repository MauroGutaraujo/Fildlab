import { describe,expect,it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi,renderWithProviders } from "../../test/utils";
import { SupervisionRul } from "./SupervisionRul";

const ruta="/api/v1/equipos/supervision-rul";
const normal={estado:"NORMAL",avisos:[],consultado_en:"2026-10-22T15:00:00Z",ultima_exitosa_en:"2026-10-22T08:02:00Z",
  total_equipos:4,equipos_sin_evaluar:0,ejecuciones_sin_cierre:0};

describe("Supervisión operativa de IA",()=>{
  it("Gerencia ve aviso de señal perdida sin abrir el historial",async()=>{
    mockApi([{path:ruta,body:{...normal,estado:"ATENCION",avisos:[{codigo:"ACTIVIDAD_NO_CONFIRMADA",severidad:"AVISO",mensaje:"Se perdió la señal de actividad; revisar la ejecución.",ejecucion_id:"run1"}]}}]);
    renderWithProviders(<SupervisionRul/>);
    expect(await screen.findByRole("alert")).toHaveTextContent(/se perdió la señal/i);
    expect(screen.queryByText(/supervisión al día/i)).not.toBeInTheDocument();
  });

  it("error de consulta no muestra normal y permite reintentar",async()=>{
    const rutas:{path:string;status:number;body:unknown}[]=[{path:ruta,status:503,body:{detail:"No disponible"}}];
    mockApi(rutas);renderWithProviders(<SupervisionRul/>);
    expect(await screen.findByRole("alert")).toHaveTextContent(/no disponible/i);
    expect(screen.queryByText(/supervisión al día/i)).not.toBeInTheDocument();
    rutas[0]={path:ruta,status:200,body:normal};
    await userEvent.click(screen.getByRole("button",{name:/reintentar supervisión/i}));
    expect(await screen.findByText(/supervisión al día/i)).toBeInTheDocument();
  });

  it("Técnico no realiza consulta administrativa",()=>{
    const f=mockApi([]);renderWithProviders(<SupervisionRul/>,{rol:"TECNICO"});
    expect(screen.queryByRole("region",{name:/supervisión de IA/i})).not.toBeInTheDocument();
    expect(f).not.toHaveBeenCalled();
  });
});
