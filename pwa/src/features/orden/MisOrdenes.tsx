import { useQuery } from "@tanstack/react-query";
import { db } from "../../db/dexie";

const ETIQUETA_ESTADO: Record<string, string> = {
  pendiente: "Pendiente de sincronizar",
  sincronizando: "Sincronizando…",
  sincronizada: "Sincronizada",
  error: "Error",
  borrador: "Borrador",
};

/** Review Focus 3 / spec §3.6: las órdenes en error deben quedar visibles, nunca desaparecer
 * en silencio (RNF-04). Se lee vía TanStack Query para poder invalidarse desde "Sincronizar
 * ahora" (App.tsx) y refrescar la lista automáticamente tras cada pasada del Outbox. */
export function MisOrdenes() {
  const { data: ordenes = [] } = useQuery({
    queryKey: ["ordenesLocal"],
    queryFn: async () => (await db.ordenesLocal.toArray()).sort((a, b) => b.creado_en_local.localeCompare(a.creado_en_local)),
  });

  return (
    <section className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Mis órdenes</h1>
      {ordenes.length === 0 ? (
        <p className="text-slate-500">No hay órdenes registradas en este dispositivo.</p>
      ) : (
        <ul className="space-y-2">
          {ordenes.map((o) => (
            <li key={o.id} className="rounded border border-slate-200 p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-mono">{o.id.slice(0, 8)}</span>
                <span className={o.estado_sync === "error" ? "font-medium text-red-700" : "text-slate-600"}>
                  {ETIQUETA_ESTADO[o.estado_sync] ?? o.estado_sync}
                </span>
              </div>
              <p className="text-xs text-slate-500">{o.equipo_serie} · {o.tipo_intervencion}</p>
              {o.error_detalle && <p className="mt-1 text-sm text-red-700">{o.error_detalle}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
