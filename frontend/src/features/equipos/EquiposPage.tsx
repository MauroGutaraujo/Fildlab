import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { DataTable } from "../../components/DataTable";
import { FormField, SelectField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { errorRuc, hoyISO, mensajeDe } from "../../lib/validators";

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

type NivelAlerta = "VERDE" | "AMARILLO" | "ROJO";
type PrediccionRul = { equipo_serie: string; dias_vida_util_remanente: number; nivel_alerta: NivelAlerta };

function clasificarRul(dias: number): { label: string; color: string } {
  if (dias > 60) return { label: "Óptimo", color: "border-emerald-200 bg-emerald-50 text-emerald-800" };
  if (dias >= 15) return { label: "Mantenimiento próximo", color: "border-amber-200 bg-amber-50 text-amber-900" };
  return { label: "Intervención urgente", color: "border-rose-200 bg-rose-50 text-rose-800" };
}

function BadgeAlerta({ prediccion }: { prediccion: PrediccionRul | undefined }) {
  if (!prediccion) {
    return (
      <span className="inline-block rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-500">
        Sin evaluar
      </span>
    );
  }
  const estado = clasificarRul(prediccion.dias_vida_util_remanente);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${estado.color}`}>
      <span aria-hidden="true" className="h-2 w-2 rounded-full bg-current" />
      {estado.label} · {prediccion.dias_vida_util_remanente} días
    </span>
  );
}

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
type Errores = Partial<Record<"serie" | "ruc" | "fecha" | ClaveParametro, string>>;

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
  });
  const prediccionPorSerie = new Map((predicciones.data ?? []).map((p) => [p.equipo_serie, p]));
  const enRiesgo = (predicciones.data ?? []).filter((p) => p.dias_vida_util_remanente < 15);
  const [detalleEquipo, setDetalleEquipo] = useState<Equipo | null>(null);
  const [mantenimientoConfirmado, setMantenimientoConfirmado] = useState<string | null>(null);
  const marcarMantenimiento = useMutation({
    mutationFn: (serie: string) => apiFetch<Equipo>(`/equipos/${serie}/marcar-mantenimiento`, { method: "POST" }),
    onSuccess: (_equipo, serie) => setMantenimientoConfirmado(serie),
  });

  const [abierto, setAbierto] = useState(false);
  const [serie, setSerie] = useState("");
  const [ruc, setRuc] = useState("");
  const [tipo, setTipo] = useState<Tipo>("OSMOSIS_INVERSA");
  const [fecha, setFecha] = useState("");
  const [params, setParams] = useState<Record<ClaveParametro, string>>(
    () => Object.fromEntries(PARAMETROS.map((p) => [p.clave, ""])) as Record<ClaveParametro, string>,
  );
  const [errores, setErrores] = useState<Errores>({});

  const crear = useMutation({
    mutationFn: (parametros: Record<string, unknown>) =>
      apiFetch<Equipo>("/equipos", {
        method: "POST",
        body: {
          serie: serie.trim(),
          cliente_ruc: ruc,
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

  function abrir() {
    crear.reset();
    setErrores({});
    setSerie("");
    setRuc("");
    setTipo("OSMOSIS_INVERSA");
    setFecha("");
    setParams(Object.fromEntries(PARAMETROS.map((p) => [p.clave, ""])) as Record<ClaveParametro, string>);
    setAbierto(true);
  }

  function enviar() {
    const e: Errores = {};
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
        {puedeEscribir && !abierto && (
          <button type="button" onClick={abrir} className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
            Nuevo equipo
          </button>
        )}
      </div>

      {abierto && (
        <FormPanel title="Nuevo equipo" onSubmit={enviar} onCancel={() => setAbierto(false)} saving={crear.isPending} error={mensajeDe(crear.error)}>
          <FormField label="Serie" value={serie} onChange={(e) => setSerie(e.target.value)} error={errores.serie} />
          <FormField label="RUC del cliente" value={ruc} onChange={(e) => setRuc(e.target.value)} inputMode="numeric" error={errores.ruc} />
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
        </FormPanel>
      )}

      <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4">
        <h2 className="mb-1 text-sm font-bold text-rose-900">Equipos en riesgo crítico de falla</h2>
        {predicciones.isLoading ? (
          <p className="text-sm text-rose-800">Cargando…</p>
        ) : predicciones.isError ? (
          <p className="text-sm text-rose-800">No se pudieron cargar las predicciones RUL</p>
        ) : enRiesgo.length === 0 ? (
          <p className="text-sm text-rose-800">Sin datos disponibles</p>
        ) : (
          <ul className="list-inside list-disc text-sm text-rose-800">
            {enRiesgo.map((p) => (
              <li key={p.equipo_serie}>{p.equipo_serie} — {p.dias_vida_util_remanente} días restantes</li>
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
            header: "RUL",
            cell: (e) => (
              <div className="flex flex-col items-start gap-1">
                <BadgeAlerta prediccion={prediccionPorSerie.get(e.serie)} />
                {puedeEscribir && (
                  mantenimientoConfirmado === e.serie ? (
                    <span className="text-xs font-medium text-emerald-600">
                      Registrado — se reflejará en el próximo cálculo
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => marcarMantenimiento.mutate(e.serie)}
                      disabled={marcarMantenimiento.isPending}
                      className="text-xs font-semibold text-blue-600 hover:text-blue-800 hover:underline cursor-pointer disabled:opacity-60"
                    >
                      Marcar mantenimiento
                    </button>
                  )
                )}
              </div>
            ),
          },
        ]}
      />

      {detalleEquipo && <ModalParametros equipo={detalleEquipo} onCerrar={() => setDetalleEquipo(null)} />}
    </section>
  );
}
