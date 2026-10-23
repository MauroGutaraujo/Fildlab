import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ApiError, apiFetch } from "../../api/client";
import { FormField, SelectField, TextAreaField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { mensajeDe } from "../../lib/validators";
import { fechaLima, TRABAJOS, type Componente, type OrdenFirmada, type Trabajo } from "./mantenimientoTypes";

export function FormularioCambioFicha({ base, componente, instalacionEquipo, accion, onGuardar, onCancelar, onRecargarFicha }: {
  base: string; componente: Componente; instalacionEquipo: string; accion: "correcciones" | "restablecer-alta";
  onGuardar: (c: Componente) => void; onCancelar: () => void; onRecargarFicha: () => Promise<Componente | undefined>;
}) {
  const [solicitudId, setSolicitudId] = useState(() => crypto.randomUUID());
  const [revision, setRevision] = useState(componente.revision);
  const [nombre, setNombre] = useState(componente.nombre);
  const [tipo, setTipo] = useState(componente.tipo_componente);
  const [fecha, setFecha] = useState(componente.fecha_instalacion ?? "");
  const [fabricante, setFabricante] = useState(componente.fabricante_modelo ?? "");
  const [motivo, setMotivo] = useState("");
  const [enviada, setEnviada] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRestablecer = accion === "restablecer-alta";
  const guardar = useMutation({ mutationFn: () => apiFetch<Componente>(`${base}/componentes/${componente.id}/${accion}`, { method: "POST", body: {
    solicitud_id: solicitudId, revision_esperada: revision, motivo: motivo.trim(), nombre: nombre.trim(), tipo_componente: tipo,
    fecha_instalacion: fecha || null, fabricante_modelo: fabricante.trim() || null,
  } }), onSuccess: onGuardar });
  async function recargarFicha() {
    const actualizada = await onRecargarFicha();
    if (!actualizada) return;
    setSolicitudId(crypto.randomUUID()); setRevision(actualizada.revision); setNombre(actualizada.nombre);
    setTipo(actualizada.tipo_componente); setFecha(actualizada.fecha_instalacion ?? "");
    setFabricante(actualizada.fabricante_modelo ?? ""); setMotivo(""); setError(null); setEnviada(false); guardar.reset();
  }
  function enviar() {
    setError(null);
    if (!nombre.trim() || !motivo.trim()) return setError("Completa la ficha y el motivo de la operación");
    if (fecha && (fecha < instalacionEquipo || fecha > fechaLima())) return setError("Revisa la fecha de instalación del componente");
    if (!guardar.isPending) { setEnviada(true); guardar.mutate(); }
  }
  return <FormPanel title={esRestablecer ? "Restablecer alta" : "Corregir ficha del componente"} submitLabel={esRestablecer ? "Guardar restablecimiento" : "Guardar corrección"} onSubmit={enviar} onCancel={onCancelar} saving={guardar.isPending} error={error ?? mensajeDe(guardar.error)}>
    <FormField label="Nombre o posición" value={nombre} disabled={enviada} maxLength={80} onChange={(e) => setNombre(e.target.value)} />
    <SelectField label="Tipo de componente" value={tipo} disabled={enviada} onChange={(e) => setTipo(e.target.value as Componente["tipo_componente"])}>
      <option value="MEMBRANA">Membrana</option><option value="FILTRO">Filtro</option><option value="RESINA">Resina</option><option value="OTRO">Otro</option>
    </SelectField>
    <FormField label="Instalación del componente si se conoce" type="date" value={fecha} disabled={enviada} min={instalacionEquipo} max={fechaLima()} onChange={(e) => setFecha(e.target.value)} />
    <FormField label="Fabricante y modelo si se conoce" value={fabricante} disabled={enviada} maxLength={120} onChange={(e) => setFabricante(e.target.value)} />
    <TextAreaField label={esRestablecer ? "Motivo de restablecimiento" : "Motivo de corrección"} value={motivo} disabled={enviada} maxLength={2000} rows={3} onChange={(e) => setMotivo(e.target.value)} />
    {guardar.error instanceof ApiError && guardar.error.status === 409 && <button type="button" onClick={() => void recargarFicha()} className="text-sm font-semibold text-blue-700">Recargar ficha explícitamente</button>}
    <p className="text-sm text-slate-600 sm:col-span-2">Se enviará la revisión {revision}. Tras el primer intento, el contenido queda bloqueado para que cada reintento use el mismo UUID y cuerpo. Un conflicto conserva este borrador; recarga la ficha solo si quieres reemplazarlo.</p>
  </FormPanel>;
}

export function FormularioAnularAlta({ base, componente, onGuardar, onCancelar, onRecargarFicha }: {
  base: string; componente: Componente; onGuardar: () => void; onCancelar: () => void;
  onRecargarFicha: () => Promise<Componente | undefined>;
}) {
  const [solicitudId, setSolicitudId] = useState(() => crypto.randomUUID());
  const [revision, setRevision] = useState(componente.revision);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviada, setEnviada] = useState(false);
  const guardar = useMutation({ mutationFn: () => apiFetch(`${base}/componentes/${componente.id}/anular-alta`, { method: "POST", body: {
    solicitud_id: solicitudId, revision_esperada: revision, motivo: motivo.trim(),
  } }), onSuccess: onGuardar });
  async function recargarFicha() {
    const actualizada = await onRecargarFicha();
    if (!actualizada) return;
    setSolicitudId(crypto.randomUUID()); setRevision(actualizada.revision); setEnviada(false); guardar.reset(); setError(null);
  }
  return <FormPanel title="Anular alta equivocada" submitLabel="Confirmar anulación del alta" onSubmit={() => {
    setError(null); if (!motivo.trim()) return setError("Indica el motivo de anulación del alta");
    if (!guardar.isPending) { setEnviada(true); guardar.mutate(); }
  }} onCancel={onCancelar} saving={guardar.isPending} error={error ?? mensajeDe(guardar.error)}>
    <TextAreaField label="Motivo de anulación del alta" value={motivo} disabled={enviada} maxLength={2000} rows={3} onChange={(e) => setMotivo(e.target.value)} />
    {guardar.error instanceof ApiError && guardar.error.status === 409 && <button type="button" onClick={() => void recargarFicha()} className="text-sm font-semibold text-blue-700">Recargar ficha explícitamente</button>}
    <p className="text-sm text-slate-600 sm:col-span-2">Se enviará la revisión {revision}. El motivo queda bloqueado tras el primer intento para conservar el UUID y cuerpo del reintento.</p>
    <p className="text-sm text-slate-600 sm:col-span-2">La anulación administrativa conserva el registro. No representa una sustitución física y requiere que no haya intervenciones vigentes.</p>
  </FormPanel>;
}

export function FormularioComponente({ base, instalacionEquipo, onGuardar, onCancelar }: {
  base: string; instalacionEquipo: string; onGuardar: (c: Componente) => void; onCancelar: () => void;
}) {
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<Componente["tipo_componente"]>("MEMBRANA");
  const [fecha, setFecha] = useState("");
  const [fabricante, setFabricante] = useState("");
  const [error, setError] = useState<string | null>(null);
  const guardar = useMutation({ mutationFn: () => apiFetch<Componente>(`${base}/componentes`, { method: "POST", body: {
    nombre: nombre.trim(), tipo_componente: tipo, fecha_instalacion: fecha || null, fabricante_modelo: fabricante.trim() || null,
  } }), onSuccess: onGuardar });
  function enviar() {
    setError(null);
    if (!nombre.trim()) return setError("Indica el nombre o posición del componente");
    if (fecha && (fecha < instalacionEquipo || fecha > fechaLima())) return setError("Revisa la fecha de instalación del componente");
    guardar.mutate();
  }
  return <FormPanel title="Registrar componente" onSubmit={enviar} onCancel={onCancelar} saving={guardar.isPending} error={error ?? mensajeDe(guardar.error)}>
    <FormField label="Nombre o posición" value={nombre} maxLength={80} placeholder="Membrana etapa 1" onChange={(e) => setNombre(e.target.value)} />
    <SelectField label="Tipo de componente" value={tipo} onChange={(e) => setTipo(e.target.value as Componente["tipo_componente"])}>
      <option value="MEMBRANA">Membrana</option><option value="FILTRO">Filtro</option><option value="RESINA">Resina</option><option value="OTRO">Otro</option>
    </SelectField>
    <FormField label="Instalación del componente si se conoce" type="date" value={fecha} min={instalacionEquipo} max={fechaLima()} onChange={(e) => setFecha(e.target.value)} />
    <FormField label="Fabricante y modelo si se conoce" value={fabricante} maxLength={120} onChange={(e) => setFabricante(e.target.value)} />
    <p className="text-sm text-slate-600 sm:col-span-2">Deja la instalación vacía si no hay evidencia de su fecha. El registro no crea una predicción de vida útil para esta pieza.</p>
  </FormPanel>;
}

export function FormularioIntervencion({ base, componente, instalacionEquipo, onGuardar, onCancelar }: {
  base: string; componente: Componente; instalacionEquipo: string; onGuardar: () => void; onCancelar: () => void;
}) {
  const [id] = useState(() => crypto.randomUUID());
  const [ordenId, setOrdenId] = useState("");
  const [tipo, setTipo] = useState<Trabajo>("INSPECCION");
  const [fecha, setFecha] = useState("");
  const [observacion, setObservacion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const ordenes = useQuery({ queryKey: ["ordenes-firmadas", base], queryFn: () => apiFetch<OrdenFirmada[]>(`${base}/ordenes-firmadas`) });
  const orden = ordenes.data?.find((o) => o.id === ordenId);
  const guardar = useMutation({ mutationFn: () => apiFetch(`${base}/componentes/${componente.id}/intervenciones`, { method: "POST", body: {
    id, orden_id: ordenId, tipo, fecha_efectiva: fecha, observacion: observacion.trim(),
  } }), onSuccess: onGuardar });
  function enviar() {
    setError(null);
    if (ordenes.isError || ordenes.isPending || !orden || !fecha || !observacion.trim()) return setError("Selecciona una orden firmada e indica fecha y observación");
    if (fecha < (componente.fecha_instalacion ?? instalacionEquipo) || fecha > fechaLima()
      || fecha > fechaLima(new Date(orden.fecha_creacion_cliente))) return setError("Revisa la fecha efectiva respecto a la instalación y al cierre de la orden");
    guardar.mutate();
  }
  return <FormPanel title={`Registrar intervención en ${componente.nombre}`} onSubmit={enviar} onCancel={onCancelar} saving={guardar.isPending} error={error ?? mensajeDe(guardar.error)}>
    <SelectField label="Orden firmada" value={ordenId} disabled={ordenes.isPending || ordenes.isError} onChange={(e) => setOrdenId(e.target.value)}>
      <option value="">Selecciona una orden</option>
      {(ordenes.data ?? []).map((o) => <option key={o.id} value={o.id}>{fechaLima(new Date(o.fecha_creacion_cliente))} · {o.tipo_intervencion} · {o.id.slice(0,8)}</option>)}
    </SelectField>
    <SelectField label="Trabajo realizado" value={tipo} onChange={(e) => setTipo(e.target.value as Trabajo)}>
      {Object.entries(TRABAJOS).map(([clave,label]) => <option key={clave} value={clave}>{label}</option>)}
    </SelectField>
    <FormField label="Fecha efectiva del trabajo en Lima" type="date" value={fecha} min={componente.fecha_instalacion ?? instalacionEquipo} max={fechaLima()} onChange={(e) => setFecha(e.target.value)} />
    <TextAreaField label="Observación" value={observacion} maxLength={2000} rows={3} onChange={(e) => setObservacion(e.target.value)} />
    {ordenes.isPending && <p role="status">Cargando órdenes firmadas…</p>}
    {ordenes.isError && <div role="alert">{mensajeDe(ordenes.error)} <button type="button" onClick={() => void ordenes.refetch()}>Reintentar órdenes</button></div>}
    {ordenes.isSuccess && ordenes.data.length === 0 && <p>No hay órdenes firmadas para este equipo. Sincroniza una orden antes de registrar la intervención.</p>}
    <p className="text-sm text-slate-600 sm:col-span-2">Solo la sustitución inicia un ciclo nuevo de este componente. Este registro de Gerencia se vincula al acta sin cambiar el documento firmado.</p>
  </FormPanel>;
}
