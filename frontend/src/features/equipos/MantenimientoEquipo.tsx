import { useId, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { SelectField } from "../../components/FormField";
import { mensajeDe } from "../../lib/validators";
import { FormularioAnularAlta, FormularioCambioFicha, FormularioComponente, FormularioIntervencion } from "./FormulariosMantenimiento";
import { HistorialComponente } from "./HistorialComponente";
import type { Componente } from "./mantenimientoTypes";

const TIPO_COMPONENTE: Record<Componente["tipo_componente"], string> = {
  MEMBRANA: "Membrana", FILTRO: "Filtro", RESINA: "Resina", OTRO: "Otro",
};

export function MantenimientoEquipo({ serie, fechaInstalacion, onCerrar }: {
  serie: string; fechaInstalacion: string; onCerrar: () => void;
}) {
  const titulo = useId();
  const puedeEscribir = useAuth().user?.rol === "GERENCIA";
  const base = `/equipos/${encodeURIComponent(serie)}`;
  const qc = useQueryClient();
  const [mostrarAnulados, setMostrarAnulados] = useState(false);
  const rutaComponentes = `${base}/componentes${mostrarAnulados ? "?incluir_anulados=true" : ""}`;
  const componentes = useQuery({ queryKey: ["componentes", base, mostrarAnulados], queryFn: () => apiFetch<Componente[]>(rutaComponentes) });
  const [seleccion, setSeleccion] = useState("");
  const [alta, setAlta] = useState(false);
  const [intervenir, setIntervenir] = useState(false);
  const [accionFicha, setAccionFicha] = useState<"correcciones" | "restablecer-alta" | "anular" | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const componente = componentes.data?.find((c) => c.id === seleccion);
  function cambio(texto: string) {
    setMensaje(texto); setIntervenir(false);
    void qc.invalidateQueries({ queryKey: ["componentes", base] });
    void qc.invalidateQueries({ queryKey: ["intervenciones", base] });
    void qc.invalidateQueries({ queryKey: ["cambios-componente", base] });
  }
  return <div role="dialog" aria-modal="true" aria-labelledby={titulo} className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-3">
    <div className="max-h-[92vh] w-full max-w-3xl space-y-4 overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
      <div className="flex items-start justify-between gap-4">
        <h2 id={titulo} className="text-lg font-bold">Componentes y mantenimiento · {serie}</h2>
        <button type="button" onClick={onCerrar} className="text-sm font-semibold text-blue-700">Cerrar mantenimiento</button>
      </div>
      <p className="text-sm text-slate-600">Cada componente conserva su propio ciclo. Las inspecciones, limpiezas y reparaciones parciales no reinician su antigüedad. La estimación de IA del sistema usa su instalación original. Anular un alta es una corrección administrativa y no representa una sustitución física.</p>
      {mensaje && <p role="status" className="text-sm font-semibold text-emerald-700">{mensaje}</p>}
      {componentes.isPending && <p role="status">Cargando componentes…</p>}
      {componentes.isError && <div role="alert" className="text-rose-700">{mensajeDe(componentes.error)} <button type="button" onClick={() => void componentes.refetch()}>Reintentar componentes</button></div>}
      {puedeEscribir && !alta && <button type="button" className="text-sm font-semibold text-blue-700" onClick={() => {setAlta(true);setIntervenir(false);setMensaje(null);}}>Agregar componente</button>}
      <label className="ml-4 inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={mostrarAnulados} onChange={(e) => {setMostrarAnulados(e.target.checked);setAccionFicha(null);setIntervenir(false);}} />Mostrar altas anuladas</label>
      {alta && puedeEscribir && <FormularioComponente base={base} instalacionEquipo={fechaInstalacion} onCancelar={() => setAlta(false)}
        onGuardar={(c) => {setAlta(false);setSeleccion(c.id);cambio("Componente registrado");}} />}
      {componentes.isSuccess && componentes.data.length === 0 && <p className="text-sm text-slate-500">Sin componentes registrados. No se han inferido piezas a partir del tipo de equipo.</p>}
      <SelectField label="Componente" value={seleccion} disabled={componentes.isPending || componentes.isError} onChange={(e) => {setSeleccion(e.target.value);setIntervenir(false);setMensaje(null);}}>
        <option value="">Selecciona un componente</option>
        {(componentes.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
      </SelectField>
      {componente && <div className="space-y-4 border-t border-slate-200 pt-4">
        {componente.anulado_en && <p className="rounded-lg bg-rose-50 p-3 text-sm font-semibold text-rose-800">Alta anulada el {componente.anulado_en.slice(0,10)} · revisión {componente.revision}. No hay ciclo operativo.</p>}
        <p className="text-sm">Tipo de componente: {TIPO_COMPONENTE[componente.tipo_componente]}</p>
        <p className="text-sm">Instalación inicial: {componente.fecha_instalacion ?? "Desconocida"}</p>
        <p className="text-sm font-medium">{componente.ciclo_actual_desde ? `Inicio del ciclo actual: ${componente.ciclo_actual_desde}` : "Inicio de ciclo desconocido"}</p>
        {componente.fabricante_modelo && <p className="text-sm text-slate-600">Fabricante/modelo declarado: {componente.fabricante_modelo}</p>}
        {puedeEscribir && !componente.anulado_en && accionFicha === null && !intervenir && !alta && <div className="flex flex-wrap gap-4">
          <button type="button" className="text-sm font-semibold text-blue-700" onClick={() => setAccionFicha("correcciones")}>Corregir ficha</button>
          <button type="button" className="text-sm font-semibold text-rose-700" onClick={() => setAccionFicha("anular")}>Anular alta equivocada</button>
          <button type="button" className="text-sm font-semibold text-blue-700" onClick={() => {setIntervenir(true);setMensaje(null);}}>Registrar intervención</button>
        </div>}
        {puedeEscribir && componente.anulado_en && accionFicha === null && <button type="button" className="text-sm font-semibold text-blue-700" onClick={() => setAccionFicha("restablecer-alta")}>Restablecer alta</button>}
        {puedeEscribir && accionFicha === "correcciones" && <FormularioCambioFicha key={`corregir-${componente.id}`} accion="correcciones" base={base} componente={componente} instalacionEquipo={fechaInstalacion}
          onRecargarFicha={async () => (await componentes.refetch()).data?.find((c) => c.id === componente.id)}
          onCancelar={() => setAccionFicha(null)} onGuardar={() => {setAccionFicha(null);cambio("Ficha corregida");}} />}
        {puedeEscribir && accionFicha === "restablecer-alta" && <FormularioCambioFicha key={`restablecer-${componente.id}`} accion="restablecer-alta" base={base} componente={componente} instalacionEquipo={fechaInstalacion}
          onRecargarFicha={async () => (await componentes.refetch()).data?.find((c) => c.id === componente.id)}
          onCancelar={() => setAccionFicha(null)} onGuardar={() => {setAccionFicha(null);cambio("Alta restablecida");}} />}
        {puedeEscribir && accionFicha === "anular" && <FormularioAnularAlta base={base} componente={componente}
          onRecargarFicha={async () => (await componentes.refetch()).data?.find((c) => c.id === componente.id)}
          onCancelar={() => setAccionFicha(null)} onGuardar={() => {setAccionFicha(null);setMostrarAnulados(true);cambio("Alta anulada");}} />}
        {puedeEscribir && !componente.anulado_en && intervenir && <FormularioIntervencion key={`form-${componente.id}`} base={base} componente={componente} instalacionEquipo={fechaInstalacion}
          onCancelar={() => setIntervenir(false)} onGuardar={() => cambio("Intervención registrada")} />}
        <HistorialComponente key={`historial-${componente.id}`} base={base} componenteId={componente.id} puedeEscribir={puedeEscribir} onCambio={cambio} />
      </div>}
    </div>
  </div>;
}
