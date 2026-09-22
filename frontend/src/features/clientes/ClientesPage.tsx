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
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Clientes</h1>
        {puedeEscribir && !abierto && (
          <button type="button" onClick={() => abrir(null)} className="rounded bg-sky-700 px-4 py-2 text-white">
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
