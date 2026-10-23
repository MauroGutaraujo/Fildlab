import { describe, expect, it, vi, afterEach } from "vitest";
import { act, screen } from "@testing-library/react";
import { renderWithProviders } from "../../test/utils";
import { esEstimacion, ResultadoRul, useRelojRul, type PrediccionRul } from "./PrediccionRul";

const p: PrediccionRul = {
  equipo_serie:"EQ-1",dias_vida_util_remanente:12,nivel_alerta:"ROJO",actualizado_en:"2026-10-21T15:00:00Z",
  vence_en:"2026-10-23T15:00:00Z",ejecucion_id:"run-1",tipo_referencia:"FILTRO",
  estado_estimacion:"ESTIMADA",motivo_no_estimable:null,version_calculo:"COX_INSTALACION_V3",
  version_dataset:"WEIBULL_CENSURA_V2",experimental:true,origen_datos:"SINTETICOS",politica_alerta:"RUL_30_90_V1",
  fecha_referencia:"2026-01-01",alcance_estimacion:"SISTEMA_DESDE_INSTALACION",
};

afterEach(()=>vi.useRealTimers());

describe("vigencia RUL en el panel",()=>{
  it("al llegar al vencimiento oculta cifra y prioridad aunque conserve respuesta en caché",()=>{
    vi.useFakeTimers(); vi.setSystemTime(new Date("2026-10-23T15:00:00Z"));
    renderWithProviders(<ResultadoRul prediccion={p}/>);
    expect(screen.getByText(/estimación vencida/i)).toBeInTheDocument();
    expect(screen.queryByText(/12 días/)).not.toBeInTheDocument();
    expect(esEstimacion(p)).toBe(false);
  });

  it("sin vencimiento no presenta una cifra como vigente",()=>{
    vi.useFakeTimers(); vi.setSystemTime(new Date("2026-10-22T15:00:00Z"));
    const legado={...p,vence_en:null};
    renderWithProviders(<ResultadoRul prediccion={legado}/>);
    expect(screen.getByText(/recálculo pendiente/i)).toBeInTheDocument();
    expect(esEstimacion(legado)).toBe(false);
  });

  it("vencida declarada por servidor permanece sin cifra",()=>{
    renderWithProviders(<ResultadoRul prediccion={{...p,estado_estimacion:"VENCIDA",dias_vida_util_remanente:null,nivel_alerta:null}}/>);
    expect(screen.getByText(/estimación vencida/i)).toBeInTheDocument();
  });

  it("una pantalla abierta retira la cifra al vencer sin esperar otra respuesta",()=>{
    vi.useFakeTimers(); vi.setSystemTime(new Date("2026-10-23T14:59:59Z"));
    function PantallaAbierta() {
      useRelojRul([p]);
      return <ResultadoRul prediccion={p}/>;
    }
    renderWithProviders(<PantallaAbierta/>);
    expect(screen.getByText(/12 días/)).toBeInTheDocument();
    act(()=>vi.advanceTimersByTime(1000));
    expect(screen.queryByText(/12 días/)).not.toBeInTheDocument();
    expect(screen.getByText(/estimación vencida/i)).toBeInTheDocument();
  });
});
