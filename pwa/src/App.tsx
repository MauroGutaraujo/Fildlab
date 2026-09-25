import { useEffect, useRef, useState } from "react";
import { QueryClient, QueryClientProvider, useMutation, useQueryClient } from "@tanstack/react-query";
import { cerrarSesion, decodeTecnicoId, obtenerToken } from "./auth/session";
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
      aria-label="Sincronizar ahora"
      className="flex items-center gap-1.5 rounded-xl bg-white/15 px-3 py-1.5 text-xs font-semibold text-white shadow-xs backdrop-blur-xs hover:bg-white/25 active:scale-95 transition-all disabled:opacity-60 cursor-pointer border border-white/20"
    >
      <svg className={`h-3.5 w-3.5 ${sync.isPending ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
      <span>{sync.isPending ? "Sincronizando…" : "Sincronizar ahora"}</span>
    </button>
  );
}

function useConectividad() {
  const [enLinea, setEnLinea] = useState(() => navigator.onLine);
  useEffect(() => {
    const marcarOnline = () => setEnLinea(true);
    const marcarOffline = () => setEnLinea(false);
    window.addEventListener("online", marcarOnline);
    window.addEventListener("offline", marcarOffline);
    return () => {
      window.removeEventListener("online", marcarOnline);
      window.removeEventListener("offline", marcarOffline);
    };
  }, []);
  return enLinea;
}

function BadgeConectividad() {
  const enLinea = useConectividad();
  return (
    <span
      role="status"
      aria-label={enLinea ? "En línea" : "Sin conexión"}
      className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold border ${
        enLinea
          ? "bg-emerald-500/15 text-emerald-200 border-emerald-400/30"
          : "bg-amber-500/15 text-amber-200 border-amber-400/30"
      }`}
    >
      <span className="relative flex h-2 w-2">
        {enLinea && <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${enLinea ? "bg-emerald-400" : "bg-amber-400"}`} />
      </span>
      {enLinea ? "En línea" : "Offline"}
    </span>
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
    <section className="p-4 pb-28">
      <div className="mb-4">
        <h1 className="text-xl font-bold tracking-tight text-slate-800">Elegir equipo</h1>
        <p className="text-xs text-slate-500 font-medium">Selecciona el equipo a intervenir para abrir la orden técnica</p>
      </div>

      <div className="relative mb-4">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por serie o código…"
          className="w-full rounded-2xl border border-slate-200 bg-white pl-10 pr-4 py-3 text-sm shadow-xs focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all"
        />
      </div>

      <ul className="space-y-2.5">
        {equipos.map((e) => {
          const datos = e.datos as EquipoDatos;
          const habilitado = tieneContrato(datos);
          return (
            <li key={e.id}>
              <button
                type="button"
                aria-label={e.id}
                disabled={!habilitado}
                onClick={() => habilitado && onElegido(datos)}
                title={habilitado ? undefined : "Este equipo no tiene un contrato asignado"}
                className="group w-full flex items-center justify-between rounded-2xl border border-slate-200/90 bg-white p-3.5 text-left shadow-xs hover:border-blue-300 hover:shadow-md active:scale-[0.99] disabled:opacity-50 disabled:hover:border-slate-200 disabled:hover:shadow-none transition-all cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl font-bold ${habilitado ? "bg-gradient-to-br from-blue-50 to-sky-100 text-blue-600 border border-blue-200/50" : "bg-slate-100 text-slate-400"}`}>
                    💧
                  </div>
                  <div>
                    <span className="block font-bold text-slate-800 text-base group-hover:text-blue-600 transition-colors">{e.id}</span>
                    <span className={`inline-block mt-0.5 text-xs font-medium rounded-full px-2 py-0.5 ${habilitado ? "bg-emerald-50 text-emerald-700 border border-emerald-200/60" : "bg-amber-50 text-amber-700 border border-amber-200/60"}`}>
                      {habilitado ? `Contrato Activo #${datos.contrato_id}` : "Sin contrato asignado"}
                    </span>
                  </div>
                </div>
                <div className="flex items-center text-slate-300 group-hover:text-blue-500 transition-colors">
                  <svg className="h-5 w-5 transform group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
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

type PantallaTipo = "equipo" | "orden" | "stock" | "misOrdenes";

type NavItem = {
  pantalla: PantallaTipo;
  equipo: EquipoConContrato | null;
};

function AppInterna() {
  const [token, setToken] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  // Pila de navegación interna para retroceder cuantas veces sea necesario sin trabas
  const [pila, setPila] = useState<NavItem[]>([
    { pantalla: "equipo", equipo: null },
  ]);

  const ignorarPop = useRef(false);

  useEffect(() => {
    obtenerToken()
      .then(setToken)
      .finally(() => setCargando(false));
  }, []);

  // Al abrir la app (sobre todo instalada como PWA), la pantalla raíz "equipo" queda parada
  // justo sobre la ÚNICA entrada de historial nativo que existe (la del lanzamiento). Sin una
  // entrada de resguardo, el primer "Atrás" real agota ese historial y Android cierra la app
  // en vez de dejarle a React manejar la navegación. Empujamos un resguardo apenas montamos.
  useEffect(() => {
    try {
      window.history.pushState({ raiz: true }, "");
    } catch {}
  }, []);

  // Soporte bidireccional y múltiple con el botón Atrás de Android / Navegador
  useEffect(() => {
    const manejarPopState = () => {
      if (ignorarPop.current) {
        ignorarPop.current = false;
        return;
      }
      setPila((prev) => {
        if (prev.length > 1) {
          return prev.slice(0, -1);
        }
        return [{ pantalla: "equipo", equipo: null }];
      });

      // Ya estábamos en la raíz: no hay nada más que desapilar dentro de la app.
      // Volvemos a empujar el resguardo para que Android nunca agote el historial
      // nativo y termine cerrando la app; solo "Salir" debe cerrar la sesión.
      if (pila.length <= 1) {
        try {
          window.history.pushState({ raiz: true }, "");
        } catch {}
      }
    };

    window.addEventListener("popstate", manejarPopState);
    return () => window.removeEventListener("popstate", manejarPopState);
  }, [pila.length]);

  const actual = pila[pila.length - 1] || { pantalla: "equipo", equipo: null };
  const pantalla = actual.pantalla;
  const equipo = actual.equipo;

  const irA = (nuevaPantalla: PantallaTipo, nuevoEquipo: EquipoConContrato | null = null) => {
    // Si ya estamos exactamente en esta vista, no acumular
    if (actual.pantalla === nuevaPantalla && actual.equipo?.serie === nuevoEquipo?.serie) {
      return;
    }

    // Si se pulsa inicio (equipos), reiniciamos la pila a la raíz y retrocedemos el
    // historial nativo la misma cantidad de pasos, para que ambos permanezcan sincronizados
    if (nuevaPantalla === "equipo") {
      const pasos = pila.length - 1;
      setPila([{ pantalla: "equipo", equipo: null }]);
      if (pasos > 0) {
        ignorarPop.current = true;
        try {
          window.history.go(-pasos);
        } catch {}
      }
      return;
    }

    setPila((prev) => [...prev, { pantalla: nuevaPantalla, equipo: nuevoEquipo }]);
    try {
      window.history.pushState({ depth: pila.length }, "");
    } catch {}
  };

  const volver = () => {
    setPila((prev) => {
      if (prev.length > 1) {
        return prev.slice(0, -1);
      }
      return [{ pantalla: "equipo", equipo: null }];
    });

    ignorarPop.current = true;
    try {
      window.history.back();
    } catch {}
  };

  if (cargando) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="h-9 w-9 animate-spin rounded-full border-3 border-blue-600 border-t-transparent" />
          <p className="text-sm font-semibold text-slate-500">Cargando aplicación…</p>
        </div>
      </div>
    );
  }

  if (!token) return <LoginTurno onIngreso={() => obtenerToken().then(setToken)} />;

  const tecnicoId = decodeTecnicoId(token) ?? 1;

  return (
    <div className="min-h-screen bg-slate-50/70 flex flex-col justify-between antialiased selection:bg-blue-100 selection:text-blue-900">
      {/* Cabecera persistente de alta fidelidad con gradiente e iluminación */}
      <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 bg-gradient-to-r from-sky-900 to-indigo-950 px-4 py-3 text-white shadow-md shadow-indigo-950/20 border-b border-white/10 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          {pantalla !== "equipo" ? (
            <button
              type="button"
              onClick={volver}
              className="flex items-center gap-1.5 rounded-xl bg-white/20 px-3 py-1.5 text-xs font-bold text-white shadow-xs backdrop-blur-xs hover:bg-white/30 active:scale-95 transition-all cursor-pointer border border-white/20"
              title="Volver a la pantalla anterior"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
              </svg>
              <span>Volver</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => irA("equipo", null)}
              className="flex items-center gap-2.5 text-left cursor-pointer group"
            >
              <img src="/logo.png" alt="Fildlab" className="h-8 w-8 rounded-xl shadow-xs border border-white/25 object-contain bg-white/10 group-hover:scale-105 transition-transform" />
              <div className="leading-tight">
                <span className="block text-base font-extrabold tracking-tight text-white drop-shadow-xs">Fildlab Campo</span>
                <span className="block text-[10px] font-medium text-sky-100 tracking-wider uppercase">PWA Offline</span>
              </div>
            </button>
          )}

          {pantalla === "stock" && (
            <span className="text-xs font-semibold text-white/90 bg-white/15 px-2 py-0.5 rounded-full border border-white/20">Stock</span>
          )}
          {pantalla === "misOrdenes" && (
            <span className="text-xs font-semibold text-white/90 bg-white/15 px-2 py-0.5 rounded-full border border-white/20">Órdenes</span>
          )}
          {pantalla === "orden" && equipo && (
            <span className="text-xs font-semibold text-white/90 bg-white/15 px-2 py-0.5 rounded-full border border-white/20 truncate max-w-[120px]">{equipo.serie}</span>
          )}
        </div>

        <nav className="flex items-center gap-2 text-xs font-medium">
          <BadgeConectividad />
          <BotonSincronizar />
          <button
            type="button"
            onClick={async () => {
              await cerrarSesion();
              setToken(null);
            }}
            className="rounded-xl bg-white/10 hover:bg-white/20 active:scale-95 px-2.5 py-1.5 text-xs font-semibold text-white/90 hover:text-white transition-all cursor-pointer border border-white/10"
            title="Cerrar turno técnico"
          >
            Salir
          </button>
        </nav>
      </header>

      {/* Contenido principal según pantalla activa */}
      <main className="mx-auto w-full max-w-lg flex-1">
        {pantalla === "equipo" && (
          <EquipoPicker
            onElegido={(e) => irA("orden", e)}
          />
        )}

        {pantalla === "orden" && equipo && tecnicoId !== null && (
          <OrdenForm
            contratoId={equipo.contrato_id}
            equipoSerie={equipo.serie}
            tecnicoId={tecnicoId}
            onCerrada={() => irA("equipo", null)}
            onVolver={volver}
          />
        )}

        {pantalla === "stock" && (
          <div className="pb-28">
            <StockMovil />
          </div>
        )}

        {pantalla === "misOrdenes" && (
          <div className="pb-28">
            <MisOrdenes />
          </div>
        )}
      </main>

      {/* Barra de Navegación Inferior Flotante (Glassmorphism Bottom Navigation Bar) */}
      <nav aria-label="Navegación móvil" className="fixed bottom-3 left-4 right-4 z-30 mx-auto max-w-lg rounded-2xl border border-slate-200/90 bg-white/95 backdrop-blur-md shadow-lg shadow-slate-900/5 py-2 px-3 flex justify-around items-center">
        <button
          type="button"
          onClick={() => irA("equipo", null)}
          className={`flex flex-col items-center gap-1 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            pantalla === "equipo" || pantalla === "orden"
              ? "bg-blue-50 text-blue-600 shadow-2xs scale-105"
              : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
          }`}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={pantalla === "equipo" || pantalla === "orden" ? 2.5 : 1.8} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span className="text-[11px]">Equipos</span>
        </button>

        <button
          type="button"
          onClick={() => irA("misOrdenes", null)}
          className={`flex flex-col items-center gap-1 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            pantalla === "misOrdenes"
              ? "bg-blue-50 text-blue-600 shadow-2xs scale-105"
              : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
          }`}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={pantalla === "misOrdenes" ? 2.5 : 1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
          </svg>
          <span className="text-[11px]">Mis órdenes</span>
        </button>

        <button
          type="button"
          onClick={() => irA("stock", null)}
          className={`flex flex-col items-center gap-1 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            pantalla === "stock"
              ? "bg-blue-50 text-blue-600 shadow-2xs scale-105"
              : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
          }`}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={pantalla === "stock" ? 2.5 : 1.8} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
          <span className="text-[11px]">Stock móvil</span>
        </button>
      </nav>
    </div>
  );
}
