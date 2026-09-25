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
  FILTRO: "Filtro",
} as const;
type Tipo = keyof typeof TIPOS;

type Equipo = {
  serie: string;
  cliente_ruc: string;
  contrato_id: number | null;
  tipo_sistema: Tipo;
  fecha_instalacion: string;
  parametros_nominales: Record<string, unknown>;
};

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
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Equipos</h1>
        {puedeEscribir && !abierto && (
          <button type="button" onClick={abrir} className="rounded bg-sky-700 px-4 py-2 text-white">
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

      <DataTable
        rows={data}
        rowKey={(e) => e.serie}
        loading={isLoading}
        error={mensajeDe(error)}
        columns={[
          { header: "Serie", cell: (e) => e.serie },
          { header: "Tipo", cell: (e) => TIPOS[e.tipo_sistema] ?? e.tipo_sistema },
          { header: "Cliente (RUC)", cell: (e) => e.cliente_ruc },
          { header: "Instalación", cell: (e) => e.fecha_instalacion },
          { header: "Parámetros nominales", cell: (e) => <code className="text-xs">{JSON.stringify(e.parametros_nominales)}</code> },
        ]}
      />
    </section>
  );
}
