import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { DataTable } from "../../components/DataTable";
import { FormField } from "../../components/FormField";
import { FormPanel } from "../../components/FormPanel";
import { errorRuc, mensajeDe } from "../../lib/validators";

type Cliente = { ruc: string; razon_social: string; direccion: string; activo: boolean };
type Errores = Partial<Record<"ruc" | "razon" | "direccion", string>>;

export function ClientesPage() {
  const puedeEscribir = useAuth().user?.rol === "GERENCIA"; // RN-01
  const qc = useQueryClient();
  const { data = [], isLoading, error } = useQuery({ queryKey: ["clientes"], queryFn: () => apiFetch<Cliente[]>("/clientes") });

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<Cliente | null>(null);
  const [ruc, setRuc] = useState("");
  const [razon, setRazon] = useState("");
  const [direccion, setDireccion] = useState("");
  const [errores, setErrores] = useState<Errores>({});

  const guardar = useMutation({
    mutationFn: () =>
      editando
        ? apiFetch<Cliente>(`/clientes/${editando.ruc}`, {
            method: "PUT",
            body: { razon_social: razon.trim(), direccion: direccion.trim() },
          })
        : apiFetch<Cliente>("/clientes", {
            method: "POST",
            body: { ruc, razon_social: razon.trim(), direccion: direccion.trim() },
          }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["clientes"] });
      cerrar();
    },
  });

  function abrir(c: Cliente | null) {
    guardar.reset();
    setErrores({});
    setEditando(c);
    setRuc(c?.ruc ?? "");
    setRazon(c?.razon_social ?? "");
    setDireccion(c?.direccion ?? "");
    setAbierto(true);
  }

  function cerrar() {
    setAbierto(false);
    setEditando(null);
  }

  function enviar() {
    const e: Errores = {};
    if (!editando) {
      const r = errorRuc(ruc);
      if (r) e.ruc = r;
    }
    if (!razon.trim()) e.razon = "La razón social es obligatoria";
    if (!direccion.trim()) e.direccion = "La dirección es obligatoria";
    setErrores(e);
    if (Object.keys(e).length === 0) guardar.mutate();
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">Clínicas y laboratorios</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">Clientes</h1>
          <p className="mt-1 text-sm text-slate-500">Directorio de sedes con servicios de tratamiento de agua.</p>
        </div>
        {puedeEscribir && !abierto && (
          <button type="button" onClick={() => abrir(null)} className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
            Nuevo cliente
          </button>
        )}
      </div>

      {abierto && (
        <FormPanel
          title={editando ? `Editar cliente ${editando.ruc}` : "Nuevo cliente"}
          onSubmit={enviar}
          onCancel={cerrar}
          saving={guardar.isPending}
          error={mensajeDe(guardar.error)}
        >
          <FormField label="RUC" value={ruc} onChange={(e) => setRuc(e.target.value)} disabled={!!editando} inputMode="numeric" error={errores.ruc} />
          <FormField label="Razón social" value={razon} onChange={(e) => setRazon(e.target.value)} error={errores.razon} />
          <FormField label="Dirección" value={direccion} onChange={(e) => setDireccion(e.target.value)} error={errores.direccion} />
        </FormPanel>
      )}

      <DataTable
        rows={data}
        rowKey={(c) => c.ruc}
        loading={isLoading}
        error={mensajeDe(error)}
        onEdit={puedeEscribir ? abrir : undefined}
        columns={[
          { header: "RUC", cell: (c) => c.ruc },
          { header: "Razón social", cell: (c) => c.razon_social },
          { header: "Dirección", cell: (c) => c.direccion },
          { header: "Estado", cell: (c) => (c.activo ? "Activo" : "Anulado") },
        ]}
      />
    </section>
  );
}
