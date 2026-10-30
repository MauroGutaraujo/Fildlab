import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { DataTable } from "../../components/DataTable";
import { FormField, SelectField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { errorRuc, hoyISO, mensajeDe } from "../../lib/validators";
import { esEstimacion, ResultadoRul, useRelojRul, type PrediccionRul } from "./PrediccionRul";
import { HistorialRul, EjecucionesRul } from "./HistorialRul";
import { MantenimientoEquipo } from "./MantenimientoEquipo";
import { SupervisionRul } from "./SupervisionRul";

const TIPOS = {
  OSMOSIS_INVERSA: "Ósmosis inversa",
  ABLANDADOR: "Ablandador",
  FILTRO: "Filtro multimedia",
} as const;
type Tipo = keyof typeof TIPOS;
const COLORES_TIPO: Record<Tipo, string> = {
  OSMOSIS_INVERSA: "border-blue-200 bg-blue-50 text-blue-800",
  ABLANDADOR: "border-violet-200 bg-violet-50 text-violet-800",
  FILTRO: "border-cyan-200 bg-cyan-50 text-cyan-800",
};

type Equipo = {
  serie: string;
  cliente_ruc: string;
  contrato_id: number | null;
  tipo_sistema: Tipo;
  fecha_instalacion: string;
  parametros_nominales: Record<string, unknown>;
};

type Contrato = { id: number; cliente_ruc: string; estado: string; fecha_inicio: string; fecha_fin: string };

function formatearParametro(valor: unknown): string {
  const numero = typeof valor === "number" ? valor : Number(valor);
  if (valor === null || valor === undefined || String(valor).trim() === "" || !Number.isFinite(numero)) return "—";
  return new Intl.NumberFormat("es-PE", { maximumFractionDigits: 2 }).format(numero);
}

function BadgeParametro({ label, valor, unidad = "" }: { label: string; valor: unknown; unidad?: string }) {
  return (
    <span className="inline-flex rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700">
      {label}: {formatearParametro(valor)}{unidad ? ` ${unidad}` : ""}
    </span>
  );
}

function ModalParametros({ equipo, onCerrar }: { equipo: Equipo; onCerrar: () => void }) {
  const valores = equipo.parametros_nominales;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="parametros-nominales-titulo"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onClick={onCerrar}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 id="parametros-nominales-titulo" className="text-base font-bold text-slate-800">Parámetros nominales — {equipo.serie}</h2>
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar"
            className="text-slate-400 hover:text-slate-700 cursor-pointer"
          >
            Cerrar
          </button>
        </div>
        <div aria-label="Parámetros nominales" className="flex flex-wrap gap-2">
          {PARAMETROS.map((p) => {
            const [label, unidad] = p.label.split(" (");
            return <BadgeParametro key={p.clave} label={label} valor={valores[p.campo]} unidad={unidad?.replace(/\)$/, "")} />;
          })}
        </div>
      </div>
    </div>
  );
}

const CLAVES_PARAMETROS = [
  "tdsEntrada",
  "tdsPostMembrana",
  "tdsProductoFinal",
  "ph",
  "conductividad",
  "resistividad",
  "litrosRed",
  "litrosPura",
] as const;
type ClaveParametro = (typeof CLAVES_PARAMETROS)[number];

const PARAMETROS: { clave: ClaveParametro; campo: string; label: string; min?: number; max?: number }[] = [
  { clave: "tdsEntrada", campo: "tds_entrada_ppm", label: "TDS entrada (ppm)" },
  { clave: "tdsPostMembrana", campo: "tds_post_membrana_ppm", label: "TDS post-membrana (ppm)" },
  { clave: "tdsProductoFinal", campo: "tds_producto_final_ppm", label: "TDS producto final (ppm)" },
  { clave: "ph", campo: "ph", label: "pH", min: 0, max: 14 },
  { clave: "conductividad", campo: "conductividad_us_cm", label: "Conductividad (μS/cm)" },
  { clave: "resistividad", campo: "resistividad_mohm_cm", label: "Resistividad (MΩ·cm)" },
  { clave: "litrosRed", campo: "litros_consumidos_red", label: "Litros consumidos (agua de red)" },
  { clave: "litrosPura", campo: "litros_agua_pura", label: "Litros de agua pura" },
];
type Errores = Partial<Record<"serie" | "ruc" | "contrato" | "fecha" | ClaveParametro, string>>;

function parseNumero(texto: string): number | null {
  const v = Number(texto.trim());
  return texto.trim() !== "" && Number.isFinite(v) ? v : null;
}

export function EquiposPage() {
  const puedeEscribir = useAuth().user?.rol === "GERENCIA";
  const qc = useQueryClient();
  const { data = [], isLoading, error } = useQuery({ queryKey: ["equipos"], queryFn: () => apiFetch<Equipo[]>("/equipos") });
  const predicciones = useQuery({
    queryKey: ["equipos", "predicciones-rul"],
    queryFn: () => apiFetch<PrediccionRul[]>("/equipos/predicciones-rul"),
    refetchInterval: 60_000,
    refetchOnWindowFocus: "always",
  });
  const prediccionPorSerie = new Map((predicciones.data ?? []).map((p) => [p.equipo_serie, p]));
  useRelojRul(predicciones.data);
  const enRiesgo = (predicciones.data ?? []).filter((p) => esEstimacion(p) && p.nivel_alerta === "ROJO");
  const [historialSerie, setHistorialSerie] = useState<string | null>(null);
  const [verEjecuciones, setVerEjecuciones] = useState(false);
  const [detalleEquipo, setDetalleEquipo] = useState<Equipo | null>(null);
  const [mantenimientoEquipo, setMantenimientoEquipo] = useState<Equipo | null>(null);

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Equipo | null>(null);
  const [serie, setSerie] = useState("");
  const [ruc, setRuc] = useState("");
  const [contratoId, setContratoId] = useState("");
  const contratos = useQuery({
    queryKey: ["contratos", "cliente", ruc],
    queryFn: () => apiFetch<Contrato[]>(`/contratos?cliente_ruc=${encodeURIComponent(ruc)}`),
    enabled: abierto && !errorRuc(ruc),
  });
  const contratosDisponibles = (contratos.data ?? []).filter((c) => c.cliente_ruc === ruc && c.estado !== "ANULADO");
  const [tipo, setTipo] = useState<Tipo>("OSMOSIS_INVERSA");
  const [fecha, setFecha] = useState("");
  const [params, setParams] = useState<Record<ClaveParametro, string>>(
    () => Object.fromEntries(PARAMETROS.map((p) => [p.clave, ""])) as Record<ClaveParametro, string>,
  );
  const [errores, setErrores] = useState<Errores>({});

  const crear = useMutation({
    mutationFn: (parametros: Record<string, unknown>) =>
      editando ? apiFetch<Equipo>(`/equipos/${encodeURIComponent(editando.serie)}`, {
        method: "PUT", body: { contrato_id: Number(contratoId) },
      }) : apiFetch<Equipo>("/equipos", {
        method: "POST",
        body: {
          serie: serie.trim(),
          cliente_ruc: ruc,
          contrato_id: Number(contratoId),
          tipo_sistema: tipo,
          fecha_instalacion: fecha,
          parametros_nominales: parametros,
        },
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["equipos"] });
      setAbierto(false);
    },
  });

  function abrir(equipo: Equipo | null = null) {
    crear.reset();
    setErrores({});
    setEditando(equipo);
    setSerie("");
    setRuc(equipo?.cliente_ruc ?? "");
    setContratoId(equipo?.contrato_id == null ? "" : String(equipo.contrato_id));
    setTipo("OSMOSIS_INVERSA");
    setFecha("");
    setParams(Object.fromEntries(PARAMETROS.map((p) => [p.clave, ""])) as Record<ClaveParametro, string>);
    setAbierto(true);
  }

  function enviar() {
    const e: Errores = {};
    if (contratos.isError || contratos.isFetching || !contratosDisponibles.some((c) => String(c.id) === contratoId)) {
      e.contrato = "Selecciona un contrato válido del cliente";
    }
    if (editando) {
      setErrores(e);
      if (Object.keys(e).length === 0) crear.mutate({});
      return;
    }
    if (!serie.trim()) e.serie = "La serie es obligatoria";
    else if (serie.trim().length > 50) e.serie = "La serie admite máximo 50 caracteres";
    const r = errorRuc(ruc);
    if (r) e.ruc = r;
    if (!fecha) e.fecha = "La fecha de instalación es obligatoria";
    else if (fecha > hoyISO()) e.fecha = "La fecha de instalación no puede ser futura";

    const parametros: Record<string, number> = {};
    for (const p of PARAMETROS) {
      const v = parseNumero(params[p.clave]);
      if (v === null) e[p.clave] = "Ingresa un valor numérico";
      else if (p.min !== undefined && v < p.min) e[p.clave] = `El valor mínimo es ${p.min}`;
      else if (p.max !== undefined && v > p.max) e[p.clave] = `El valor máximo es ${p.max}`;
      else parametros[p.campo] = v;
    }

    setErrores(e);
    if (Object.keys(e).length === 0) crear.mutate(parametros);
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">Mantenimiento y vida útil</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">Equipos</h1>
          <p className="mt-1 text-sm text-slate-500">Estado preventivo y vida útil remanente por sistema.</p>
        </div>
        {puedeEscribir && (
          <div className="flex flex-wrap gap-2">
            <button type="button" className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600" onClick={()=>setVerEjecuciones(!verEjecuciones)}>
              {verEjecuciones ? "Ocultar ejecuciones de IA" : "Ver ejecuciones de IA"}
            </button>
            {!abierto && (
              <button type="button" onClick={() => abrir()} className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
                Nuevo equipo
              </button>
            )}
          </div>
        )}
      </div>

      {abierto && (
        <FormPanel title={editando ? `Editar contrato — ${editando.serie}` : "Nuevo equipo"} onSubmit={enviar} onCancel={() => setAbierto(false)} saving={crear.isPending} error={mensajeDe(crear.error)}>
          {!editando && <FormField label="Serie" value={serie} onChange={(e) => setSerie(e.target.value)} error={errores.serie} />}
          <FormField label="RUC del cliente" value={ruc} disabled={!!editando} onChange={(e) => {
            setRuc(e.target.value);
            setContratoId("");
            setErrores((prev) => ({ ...prev, contrato: undefined }));
          }} inputMode="numeric" error={errores.ruc} />
          <div>
            <SelectField label="Contrato del cliente" value={contratoId} onChange={(e) => setContratoId(e.target.value)}
              disabled={!!errorRuc(ruc) || contratos.isFetching || contratos.isError || contratosDisponibles.length === 0} error={errores.contrato}>
              <option value="">Selecciona un contrato</option>
              {contratosDisponibles.map((c) => <option key={c.id} value={c.id}>Contrato #{c.id} · {c.fecha_inicio} a {c.fecha_fin} · {c.estado}</option>)}
            </SelectField>
            {errorRuc(ruc) ? <p className="mt-1 text-sm text-slate-500">Ingresa un RUC válido para consultar sus contratos.</p>
              : contratos.isFetching ? <p role="status" className="mt-1 text-sm text-slate-500">Cargando contratos…</p>
              : contratos.isError ? <div role="alert" className="mt-1 text-sm text-rose-700">No se pudieron cargar los contratos. <button type="button" onClick={() => void contratos.refetch()} className="underline">Reintentar contratos</button></div>
              : contratosDisponibles.length === 0 ? <p className="mt-1 text-sm text-slate-500">No hay contratos disponibles para este cliente. Crea un contrato en Contratos antes de asociar el equipo.</p> : null}
          </div>
          {!editando && <>
          <SelectField label="Tipo de sistema" value={tipo} onChange={(e) => setTipo(e.target.value as Tipo)}>
            {(Object.keys(TIPOS) as Tipo[]).map((t) => (
              <option key={t} value={t}>
                {TIPOS[t]}
              </option>
            ))}
          </SelectField>
          <FormField label="Fecha de instalación" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} error={errores.fecha} />

          <div className="col-span-full">
            <h3 className="text-sm font-bold text-slate-800">Parámetros nominales de referencia</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Lecturas físico-químicas y volumétricas de fábrica que se usarán como referencia al comparar contra las lecturas registradas en cada orden de servicio.
            </p>
          </div>
          {PARAMETROS.map((p) => (
            <FormField
              key={p.clave}
              label={p.label}
              type="number"
              step="any"
              inputMode="decimal"
              value={params[p.clave]}
              onChange={(e) => setParams((prev) => ({ ...prev, [p.clave]: e.target.value }))}
              error={errores[p.clave]}
            />
          ))}
          </>}
        </FormPanel>
      )}

      {puedeEscribir && verEjecuciones && <EjecucionesRul/>}
      {puedeEscribir && <SupervisionRul/>}
      <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4">
        <h2 className="mb-1 text-sm font-bold text-rose-900">Estimaciones con prioridad alta</h2>
        {predicciones.isLoading ? (
          <p className="text-sm text-rose-800">Cargando…</p>
        ) : predicciones.isError ? (
          <p className="text-sm text-rose-800">No se pudieron cargar las predicciones RUL</p>
        ) : enRiesgo.length === 0 ? (
          <p className="text-sm text-rose-800">Sin estimaciones de prioridad alta</p>
        ) : (
          <ul className="list-inside list-disc text-sm text-rose-800">
            {enRiesgo.map((p) => (
              <li key={p.equipo_serie}>{p.equipo_serie} — {p.dias_vida_util_remanente} días estimados</li>
            ))}
          </ul>
        )}
      </div>

      <DataTable
        rows={data}
        rowKey={(e) => e.serie}
        loading={isLoading}
        error={mensajeDe(error)}
        columns={[
          { header: "Serie", cell: (e) => e.serie },
          { header: "Tipo", cell: (e) => (
            <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${COLORES_TIPO[e.tipo_sistema]}`}>
              <span aria-hidden="true" className="h-2 w-2 rounded-full bg-current" />
              {TIPOS[e.tipo_sistema] ?? e.tipo_sistema}
            </span>
          ) },
          { header: "Cliente (RUC)", cell: (e) => e.cliente_ruc },
          { header: "Contrato", cell: (e) => <div className="flex flex-col items-start gap-1">
            <span>{e.contrato_id == null ? "Sin contrato" : `Contrato #${e.contrato_id}`}</span>
            {puedeEscribir && <button type="button" onClick={() => abrir(e)} className="text-xs font-semibold text-blue-700 hover:underline">Editar contrato</button>}
          </div> },
          { header: "Instalación", cell: (e) => e.fecha_instalacion },
          {
            header: "Parámetros nominales",
            cell: (e) => (
              <div className="flex min-w-52 flex-col items-start gap-2">
                <div className="flex flex-wrap gap-1.5">
                  <BadgeParametro label="TDS" valor={e.parametros_nominales.tds_entrada_ppm} unidad="ppm" />
                  <BadgeParametro label="TDS post" valor={e.parametros_nominales.tds_post_membrana_ppm} unidad="ppm" />
                  <BadgeParametro label="pH" valor={e.parametros_nominales.ph} />
                </div>
                <button
                  type="button"
                  onClick={() => setDetalleEquipo(e)}
                  className="text-xs font-semibold text-blue-700 hover:text-blue-900 hover:underline cursor-pointer"
                >
                  Ver detalle
                </button>
              </div>
            ),
          },
          {
            header: "Vida restante del sistema",
            cell: (e) => (
              <div className="flex flex-col items-start gap-1">
                <ResultadoRul prediccion={prediccionPorSerie.get(e.serie)} />
                <button type="button" onClick={()=>setHistorialSerie(e.serie)} className="text-xs font-semibold text-blue-700 hover:underline">Historial de IA</button>
                <button type="button" onClick={() => setMantenimientoEquipo(e)} className="text-xs font-semibold text-blue-700 hover:underline">Componentes y mantenimiento</button>
              </div>
            ),
          },
        ]}
      />

      {detalleEquipo && <ModalParametros equipo={detalleEquipo} onCerrar={() => setDetalleEquipo(null)} />}
      {historialSerie && <HistorialRul key={historialSerie} serie={historialSerie} onCerrar={()=>setHistorialSerie(null)}/>}
      {mantenimientoEquipo && <MantenimientoEquipo key={mantenimientoEquipo.serie} serie={mantenimientoEquipo.serie}
        fechaInstalacion={mantenimientoEquipo.fecha_instalacion} onCerrar={() => setMantenimientoEquipo(null)} />}
    </section>
  );
}
