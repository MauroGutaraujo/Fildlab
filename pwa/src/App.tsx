import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider, useMutation, useQueryClient } from "@tanstack/react-query";
import { decodeTecnicoId, obtenerToken } from "./auth/session";
import { LoginTurno } from "./auth/LoginTurno";
import { buscarEquipos, refrescarCatalogo } from "./db/catalogo";
import type { CatalogoItem } from "./db/dexie";
import { procesarOutbox } from "./db/outbox";
import { MisOrdenes } from "./features/orden/MisOrdenes";
import { OrdenForm } from "./features/orden/OrdenForm";
import { StockMovil } from "./features/stock/StockMovil";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function BotonSincronizar() {
  const qc = useQueryClient();
  const sync = useMutation({
    mutationFn: procesarOutbox,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ordenesLocal"] }),
  });
  return (
    <button
      type="button"
      onClick={() => sync.mutate()}
      disabled={sync.isPending}
      className="rounded-lg bg-white/20 px-2.5 py-1 text-xs font-semibold text-white shadow-xs hover:bg-white/30 transition-colors disabled:opacity-60 cursor-pointer"
    >
      {sync.isPending ? "Sincronizando…" : "Sincronizar"}
    </button>
  );
}

type EquipoDatos = { serie: string; contrato_id: number | null };
type EquipoConContrato = { serie: string; contrato_id: number };

function tieneContrato(e: EquipoDatos): e is EquipoConContrato {
  return e.contrato_id !== null;
}

function EquipoPicker({ onElegido }: { onElegido: (equipo: EquipoConContrato) => void }) {
  const [query, setQuery] = useState("");
  const [equipos, setEquipos] = useState<CatalogoItem[]>([]);

  useEffect(() => {
    refrescarCatalogo().finally(() => buscarEquipos("").then(setEquipos));
  }, []);

  useEffect(() => {
    buscarEquipos(query).then(setEquipos);
  }, [query]);

  return (
    <section className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Elegir equipo</h1>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Buscar por serie…"
        className="mb-3 w-full rounded border border-slate-300 px-3 py-2"
      />
      <ul className="space-y-1">
        {equipos.map((e) => {
          const datos = e.datos as EquipoDatos;
          const habilitado = tieneContrato(datos);
          return (
            <li key={e.id}>
              <button
                type="button"
                disabled={!habilitado}
                onClick={() => habilitado && onElegido(datos)}
                title={habilitado ? undefined : "Este equipo no tiene un contrato asignado"}
                className="w-full rounded border border-slate-200 px-3 py-2 text-left hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-transparent"
              >
                {e.id}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInterna />
    </QueryClientProvider>
  );
}

function AppInterna() {
  const [token, setToken] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [equipo, setEquipo] = useState<EquipoConContrato | null>(null);
  const [pantalla, setPantalla] = useState<"equipo" | "orden" | "stock" | "misOrdenes">("equipo");

  useEffect(() => {
    obtenerToken()
      .then(setToken)
      .finally(() => setCargando(false));
  }, []);

  if (cargando) return <p className="p-6 text-slate-500">Cargando…</p>;
  if (!token) return <LoginTurno onIngreso={() => obtenerToken().then(setToken)} />;

  const tecnicoId = decodeTecnicoId(token);

  if (pantalla === "stock" || pantalla === "misOrdenes") {
    return (
      <>
        <button type="button" onClick={() => setPantalla("equipo")} className="m-2 text-sm text-sky-700 hover:underline">
          ← Volver
        </button>
        {pantalla === "stock" ? <StockMovil /> : <MisOrdenes />}
      </>
    );
  }
  if (pantalla === "orden" && equipo && tecnicoId !== null) {
    return (
      <OrdenForm
        contratoId={equipo.contrato_id}
        equipoSerie={equipo.serie}
        tecnicoId={tecnicoId}
        onCerrada={() => {
          setEquipo(null);
          setPantalla("equipo");
        }}
      />
    );
  }
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex flex-wrap items-center justify-between gap-2 bg-gradient-to-r from-blue-700 via-blue-600 to-sky-500 px-4 py-2.5 text-white shadow-md">
        <div className="flex items-center gap-2.5">
          <img src="/logo.png" alt="Fildlab" className="h-8 w-8 rounded-xl shadow-xs border border-white/20 object-contain bg-white/10" />
          <span className="text-lg font-bold tracking-tight text-white drop-shadow-sm">Fildlab Campo</span>
        </div>
        <nav className="flex items-center gap-2 text-xs font-medium">
          <BotonSincronizar />
          <button type="button" onClick={() => setPantalla("misOrdenes")} className="rounded-lg bg-white/10 px-2.5 py-1 text-white hover:bg-white/20 transition-colors">
            Mis órdenes
          </button>
          <button type="button" onClick={() => setPantalla("stock")} className="rounded-lg bg-white/10 px-2.5 py-1 text-white hover:bg-white/20 transition-colors">
            Stock móvil
          </button>
        </nav>
      </header>
      <main className="mx-auto max-w-lg">
        <EquipoPicker
          onElegido={(e) => {
            setEquipo(e);
            setPantalla("orden");
          }}
        />
      </main>
    </div>
  );
}
