import { describe, expect, it } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderWithProviders } from "../../test/utils";
import { MantenimientoEquipo } from "./MantenimientoEquipo";

const BASE = "/api/v1/equipos/EQ-1";
const C = { id:"00000000-0000-0000-0000-000000000001", equipo_serie:"EQ-1", nombre:"Membrana etapa 1",
  tipo_componente:"MEMBRANA", fecha_instalacion:null, fabricante_modelo:null, creado_por_id:1,
  creado_en:"2026-02-01T15:00:00Z", ciclo_actual_desde:null, revision:1, anulado_en:null };
const O = { id:"00000000-0000-0000-0000-000000000002", tipo_intervencion:"PREVENTIVO", fecha_creacion_cliente:"2026-02-05T17:00:00Z" };
const I = { id:"00000000-0000-0000-0000-000000000003", componente_id:C.id, orden_id:O.id,
  tipo:"LIMPIEZA", fecha_efectiva:"2026-02-01", observacion:"Limpieza sin sustituir piezas", acta_hash:"a".repeat(64),
  registrado_por_id:1, registrado_por_nombre:"Gerencia Test", registrado_en:"2026-02-05T20:00:00Z", anulacion:null };
const HIST = `${BASE}/componentes/${C.id}/intervenciones`;
const rutas = () => [{ path:`${BASE}/componentes`,body:[C] },{ path:`${BASE}/ordenes-firmadas`,body:[O] },{path:HIST,body:[I]},
  {path:/\/componentes\/[^/]+\/cambios\?limit=20&offset=\d+$/,body:[]}];
const ui = () => <MantenimientoEquipo serie="EQ-1" fechaInstalacion="2026-01-01" onCerrar={()=>{}} />;

async function seleccionar() {
  await screen.findByRole("option", { name:/Membrana etapa 1/ });
  await userEvent.selectOptions(screen.getByLabelText("Componente"), C.id);
}

describe("Mantenimiento por componentes",()=>{
  it("técnico consulta ciclos e historial sin controles de escritura",async()=>{
    mockApi(rutas()); renderWithProviders(ui(),{rol:"TECNICO"}); await seleccionar();
    expect(await screen.findByText(I.observacion)).toBeInTheDocument();
    expect(screen.getByText(/inicio de ciclo desconocido/i)).toBeInTheDocument();
    expect(screen.getByText(/tipo de componente: membrana/i)).toBeInTheDocument();
    expect(screen.getByText(/instalación inicial: desconocida/i)).toBeInTheDocument();
    expect(screen.getByText(/Gerencia Test/)).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:/agregar componente/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:/registrar intervención/i})).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:/anular registro/i})).not.toBeInTheDocument();
  });

  it("registra componente con instalación desconocida sin inventar fecha",async()=>{
    const f=mockApi([...rutas(),{method:"POST",path:`${BASE}/componentes`,status:201,body:C}]);
    renderWithProviders(ui()); await userEvent.click(screen.getByRole("button",{name:/agregar componente/i}));
    await userEvent.type(screen.getByLabelText("Nombre o posición"),"Prefiltro 1");
    await userEvent.selectOptions(screen.getByLabelText("Tipo de componente"),"FILTRO");
    await userEvent.click(screen.getByRole("button",{name:"Guardar"}));
    expect(await screen.findByText("Componente registrado")).toBeInTheDocument();
    const p=f.mock.calls.find(([,i])=>i?.method==="POST");
    expect(JSON.parse(p![1]!.body as string)).toEqual({nombre:"Prefiltro 1",tipo_componente:"FILTRO",fecha_instalacion:null,fabricante_modelo:null});
  });

  it("fecha inválida de componente no se transmite",async()=>{
    const f=mockApi(rutas()); renderWithProviders(ui());
    await userEvent.click(screen.getByRole("button",{name:/agregar componente/i}));
    await userEvent.type(screen.getByLabelText("Nombre o posición"),"Prefiltro");
    fireEvent.change(screen.getByLabelText(/instalación del componente/i),{target:{value:"2999-01-01"}});
    await userEvent.click(screen.getByRole("button",{name:"Guardar"}));
    expect(await screen.findByRole("alert")).toHaveTextContent(/fecha/i);
    expect(f.mock.calls.filter(([,i])=>i?.method==="POST")).toHaveLength(0);
  });

  it("registra intervención con orden firmada y campos explícitos",async()=>{
    const f=mockApi([...rutas(),{method:"POST",path:HIST,status:201,body:I}]);
    renderWithProviders(ui()); await seleccionar();
    await userEvent.click(screen.getByRole("button",{name:/registrar intervención/i}));
    await screen.findByRole("option",{name:/PREVENTIVO/});
    await userEvent.selectOptions(screen.getByLabelText("Orden firmada"),O.id);
    await userEvent.selectOptions(screen.getByLabelText("Trabajo realizado"),"LIMPIEZA");
    fireEvent.change(screen.getByLabelText(/fecha efectiva/i),{target:{value:"2026-02-01"}});
    await userEvent.type(screen.getByLabelText("Observación"),I.observacion);
    await userEvent.click(screen.getByRole("button",{name:"Guardar"}));
    expect(await screen.findByText("Intervención registrada")).toBeInTheDocument();
    const p=f.mock.calls.find(([url,i])=>url===HIST && i?.method==="POST");
    expect(JSON.parse(p![1]!.body as string)).toMatchObject({orden_id:O.id,tipo:"LIMPIEZA",fecha_efectiva:"2026-02-01",observacion:I.observacion});
  });

  it("conserva el formulario y UUID al reintentar un error de red",async()=>{
    const f=mockApi([...rutas(),{method:"POST",path:HIST,status:503,body:{detail:"Intenta nuevamente"}}]);
    renderWithProviders(ui()); await seleccionar();
    await userEvent.click(screen.getByRole("button",{name:/registrar intervención/i}));
    await screen.findByRole("option",{name:/PREVENTIVO/});
    await userEvent.selectOptions(screen.getByLabelText("Orden firmada"),O.id);
    fireEvent.change(screen.getByLabelText(/fecha efectiva/i),{target:{value:"2026-02-01"}});
    await userEvent.type(screen.getByLabelText("Observación"),"Inspección de la pieza");
    await userEvent.click(screen.getByRole("button",{name:"Guardar"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("Intenta nuevamente");
    expect(screen.getByLabelText("Observación")).toHaveValue("Inspección de la pieza");
    await userEvent.click(screen.getByRole("button",{name:"Guardar"}));
    await screen.findByRole("alert");
    const cuerpos=f.mock.calls.filter(([url,i])=>url===HIST && i?.method==="POST").map(([,i])=>JSON.parse(i!.body as string));
    expect(cuerpos).toHaveLength(2); expect(cuerpos[0].id).toBe(cuerpos[1].id);
  });

  it("anula con motivo sin borrar el registro",async()=>{
    mockApi([...rutas(),{method:"POST",path:`${HIST}/${I.id}/anular`,status:201,body:{id:"anulacion",intervencion_id:I.id,motivo:"Pieza equivocada",registrado_por_id:1,registrado_en:"2026-02-05T21:00:00Z"}}]);
    renderWithProviders(ui()); await seleccionar();
    await userEvent.click(await screen.findByRole("button",{name:/anular registro/i}));
    await userEvent.type(screen.getByLabelText("Motivo de anulación"),"Pieza equivocada");
    await userEvent.click(screen.getByRole("button",{name:/confirmar anulación/i}));
    expect(await screen.findByText("Anulación registrada")).toBeInTheDocument();
    expect(screen.getByText(I.observacion)).toBeInTheDocument();
  });

  it("avisa fallo de consulta y permite reintentar",async()=>{
    mockApi([{path:`${BASE}/componentes`,status:503,body:{detail:"Servicio temporalmente no disponible"}}]);
    renderWithProviders(ui());
    expect(await screen.findByRole("alert")).toHaveTextContent(/no disponible/i);
    expect(screen.getByRole("button",{name:/reintentar componentes/i})).toBeInTheDocument();
  });

  it("corrige la ficha con motivo, revisión capturada y UUID estable ante conflicto",async()=>{
    const f=mockApi([...rutas(),{method:"POST",path:`${BASE}/componentes/${C.id}/correcciones`,status:409,body:{detail:"La ficha cambió"}}]);
    renderWithProviders(ui()); await seleccionar();
    await userEvent.click(screen.getByRole("button",{name:/corregir ficha/i}));
    expect(screen.getByLabelText("Nombre o posición")).toHaveValue(C.nombre);
    await userEvent.clear(screen.getByLabelText("Nombre o posición"));
    await userEvent.type(screen.getByLabelText("Nombre o posición"),"Membrana confirmada");
    await userEvent.type(screen.getByLabelText(/motivo/i),"Verificación de etiqueta");
    await userEvent.click(screen.getByRole("button",{name:/guardar corrección/i}));
    expect(await screen.findByRole("alert")).toHaveTextContent("La ficha cambió");
    expect(screen.getByLabelText("Nombre o posición")).toHaveValue("Membrana confirmada");
    expect(screen.getByLabelText("Nombre o posición")).toBeDisabled();
    await userEvent.click(screen.getByRole("button",{name:/guardar corrección/i}));
    const bodies=f.mock.calls.filter(([url,i])=>url===`${BASE}/componentes/${C.id}/correcciones`&&i?.method==="POST").map(([,i])=>JSON.parse(i!.body as string));
    expect(bodies).toHaveLength(2);
    expect(bodies[0]).toEqual(bodies[1]);
    expect(bodies[0]).toMatchObject({revision_esperada:1,motivo:"Verificación de etiqueta",nombre:"Membrana confirmada"});
    expect(bodies[0].solicitud_id).toMatch(/^[0-9a-f-]{36}$/i);
    await userEvent.click(screen.getByRole("button",{name:/recargar ficha explícitamente/i}));
    expect(screen.getByLabelText("Nombre o posición")).toHaveValue(C.nombre);
    expect(screen.getByLabelText(/motivo de corrección/i)).toHaveValue("");
  });

  it("distingue anular alta administrativa y deja consultar los componentes anulados",async()=>{
    const f=mockApi([...rutas(),{path:`${BASE}/componentes`,body:[]},{path:`${BASE}/componentes?incluir_anulados=true`,body:[{...C,anulado_en:"2026-10-23T12:00:00Z",revision:2,ciclo_actual_desde:null}]},
      {method:"POST",path:`${BASE}/componentes/${C.id}/anular-alta`,status:201,body:{...C,anulado_en:"2026-10-23T12:00:00Z",revision:2,ciclo_actual_desde:null}}]);
    renderWithProviders(ui()); await seleccionar();
    expect(await screen.findByRole("button",{name:/anular alta equivocada/i})).toBeInTheDocument();
    expect(screen.getByText(/no representa una sustitución física/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button",{name:/anular alta equivocada/i}));
    await userEvent.type(screen.getByLabelText(/motivo de anulación del alta/i),"Registro duplicado");
    await userEvent.click(screen.getByRole("button",{name:/confirmar anulación del alta/i}));
    expect(await screen.findByRole("checkbox",{name:/mostrar altas anuladas/i})).toBeInTheDocument();
    const body=f.mock.calls.find(([url,i])=>url===`${BASE}/componentes/${C.id}/anular-alta`&&i?.method==="POST");
    expect(JSON.parse(body![1]!.body as string)).toMatchObject({revision_esperada:1,motivo:"Registro duplicado"});
    await waitFor(()=>expect(f.mock.calls.some(([url])=>url===`${BASE}/componentes?incluir_anulados=true`)).toBe(true));
  });

  it("muestra alta anulada sin permitir intervenciones y ofrece restablecerla con motivo",async()=>{
    const anulada={...C,anulado_en:"2026-10-23T12:00:00Z",revision:2,ciclo_actual_desde:null};
    const f=mockApi([{path:`${BASE}/componentes`,body:[]},{path:`${BASE}/componentes?incluir_anulados=true`,body:[anulada]},
      {path:HIST,body:[I]},{path:/\/componentes\/[^/]+\/cambios\?limit=20&offset=\d+$/,body:[]},
      {method:"POST",path:`${BASE}/componentes/${C.id}/restablecer-alta`,status:201,body:{...anulada,anulado_en:null,revision:3}}]);
    renderWithProviders(ui());
    await userEvent.click(screen.getByRole("checkbox",{name:/mostrar altas anuladas/i}));
    await seleccionar();
    expect(await screen.findByText(/alta anulada el/i)).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:/registrar intervención/i})).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button",{name:/restablecer alta/i}));
    await userEvent.type(screen.getByLabelText(/motivo de restablecimiento/i),"Alta verificada");
    await userEvent.click(screen.getByRole("button",{name:/guardar restablecimiento/i}));
    const body=f.mock.calls.find(([url,i])=>url===`${BASE}/componentes/${C.id}/restablecer-alta`&&i?.method==="POST");
    expect(JSON.parse(body![1]!.body as string)).toMatchObject({revision_esperada:2,motivo:"Alta verificada",nombre:C.nombre});
  });

  it("reintenta la anulación con el mismo UUID y motivo tras un error de red ambiguo",async()=>{
    const f=mockApi([...rutas(),{method:"POST",path:`${BASE}/componentes/${C.id}/anular-alta`,status:503,body:{detail:"Servicio temporalmente no disponible"}}]);
    renderWithProviders(ui()); await seleccionar();
    await userEvent.click(screen.getByRole("button",{name:/anular alta equivocada/i}));
    await userEvent.type(screen.getByLabelText(/motivo de anulación del alta/i),"Alta repetida");
    await userEvent.click(screen.getByRole("button",{name:/confirmar anulación del alta/i}));
    expect(await screen.findByRole("alert")).toHaveTextContent("Servicio temporalmente no disponible");
    expect(screen.getByLabelText(/motivo de anulación del alta/i)).toBeDisabled();
    await userEvent.click(screen.getByRole("button",{name:/confirmar anulación del alta/i}));
    const cuerpos=f.mock.calls.filter(([url,i])=>url===`${BASE}/componentes/${C.id}/anular-alta`&&i?.method==="POST").map(([,i])=>JSON.parse(i!.body as string));
    expect(cuerpos).toHaveLength(2);
    expect(cuerpos[0]).toEqual(cuerpos[1]);
  });

  it("conserva el motivo de anulación y ofrece recargar tras una revisión conflictiva",async()=>{
    const f=mockApi([...rutas(),{method:"POST",path:`${BASE}/componentes/${C.id}/anular-alta`,status:409,body:{detail:"La ficha cambió. Recarga su revisión"}}]);
    renderWithProviders(ui()); await seleccionar();
    await userEvent.click(screen.getByRole("button",{name:/anular alta equivocada/i}));
    await userEvent.type(screen.getByLabelText(/motivo de anulación del alta/i),"Alta equivocada");
    await userEvent.click(screen.getByRole("button",{name:/confirmar anulación del alta/i}));
    expect(await screen.findByRole("alert")).toHaveTextContent(/ficha cambió/i);
    expect(screen.getByLabelText(/motivo de anulación del alta/i)).toBeDisabled();
    await userEvent.click(screen.getByRole("button",{name:/recargar ficha explícitamente/i}));
    expect(screen.getByLabelText(/motivo de anulación del alta/i)).toHaveValue("Alta equivocada");
    expect(screen.getByLabelText(/motivo de anulación del alta/i)).not.toBeDisabled();
    await userEvent.click(screen.getByRole("button",{name:/confirmar anulación del alta/i}));
    const cuerpos=f.mock.calls.filter(([url,i])=>url===`${BASE}/componentes/${C.id}/anular-alta`&&i?.method==="POST").map(([,i])=>JSON.parse(i!.body as string));
    expect(cuerpos).toHaveLength(2);
    expect(cuerpos[0].solicitud_id).not.toBe(cuerpos[1].solicitud_id);
    expect(cuerpos[1]).toMatchObject({revision_esperada:1,motivo:"Alta equivocada"});
  });
});
