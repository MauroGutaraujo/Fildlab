import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { DataTable } from "../../components/DataTable";
import { FormField, SelectField, TextAreaField } from "../../components/FormField";
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
type Errores = Partial<Record<"serie" | "ruc" | "fecha" | "params", string>>;

const ERR_PARAMS = "Los parámetros nominales deben ser un objeto JSON no vacío";

function parseParametros(texto: string): Record<string, unknown> | null {
  try {
    const v: unknown = JSON.parse(texto);
    if (v === null || typeof v !== "object" || Array.isArray(v) || Object.keys(v).length === 0) return null;
    return v as Record<string, unknown>;
  } catch {
    return null;
  }
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
  const [params, setParams] = useState("");
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
    setParams("");
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
    const parametros = parseParametros(params);
    if (!parametros) e.params = ERR_PARAMS;
    setErrores(e);
    if (Object.keys(e).length === 0 && parametros) crear.mutate(parametros);
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
          <TextAreaField
            label="Parámetros nominales (JSON)"
            value={params}
            onChange={(e) => setParams(e.target.value)}
            rows={4}
            placeholder='{"presion_psi": 60, "conductividad_us_cm": 15}'
            error={errores.params}
          />
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
