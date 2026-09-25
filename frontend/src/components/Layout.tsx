import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Rol, useAuth } from "../auth/AuthContext";

type IconoId = "clientes" | "contratos" | "equipos" | "inventario" | "ventas" | "liquidacion";

const ICONOS: Record<IconoId, string> = {
  clientes: "M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6M9 10h.01M15 10h.01M9 14h.01M15 14h.01",
  contratos: "M7 3h8l4 4v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1zM9 9h6M9 13h6M9 17h4",
  equipos: "M12 3s6 6.5 6 11a6 6 0 11-12 0c0-4.5 6-11 6-11z",
  inventario: "M4 7l8-4 8 4-8 4-8-4zm0 0v10l8 4m0-14v14m8-14v10l-8 4",
  ventas: "M4 8h16v11a1 1 0 01-1 1H5a1 1 0 01-1-1V8zm2 0V6a2 2 0 012-2h8a2 2 0 012 2v2",
  liquidacion: "M12 3v18M6 7l-3 6a3 3 0 006 0l-3-6zm12 0l-3 6a3 3 0 006 0l-3-6zM3 7h6m6 0h6",
};

function Icono({ id, className }: { id: IconoId; className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICONOS[id]} />
    </svg>
  );
}

const ENLACES: { to: string; texto: string; icon: IconoId; roles: Rol[] }[] = [
  { to: "/clientes", texto: "Clientes", icon: "clientes", roles: ["GERENCIA", "TECNICO"] },
  { to: "/contratos", texto: "Contratos", icon: "contratos", roles: ["GERENCIA", "TECNICO"] },
  { to: "/equipos", texto: "Equipos", icon: "equipos", roles: ["GERENCIA", "TECNICO"] },
  { to: "/inventario", texto: "Inventario", icon: "inventario", roles: ["GERENCIA", "TECNICO"] },
  { to: "/ventas", texto: "Ventas", icon: "ventas", roles: ["GERENCIA"] },
  { to: "/liquidacion", texto: "Liquidación", icon: "liquidacion", roles: ["GERENCIA"] },
];

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const seccionActual = ENLACES.find((e) => location.pathname.startsWith(e.to));

  return (
    <div className="min-h-screen bg-slate-50/60 selection:bg-blue-100 selection:text-blue-900 flex flex-col justify-between">
      <div>
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-blue-950 to-indigo-950 px-5 py-3 text-white shadow-md border-b border-white/10 backdrop-blur-md">
          <div className="flex flex-wrap items-center gap-6">
            <NavLink
              to="/clientes"
              className="flex items-center gap-2.5 hover:opacity-95 transition-opacity group cursor-pointer"
              title="Ir al inicio de la plataforma"
            >
              <img
                src="/logo.png"
                alt="Fildlab"
                className="h-9 w-9 rounded-xl shadow-xs border border-white/20 object-contain bg-white/10 group-hover:scale-105 transition-transform"
              />
              <div>
                <span className="text-lg font-extrabold tracking-tight text-white drop-shadow-xs block leading-tight">
                  Fildlab
                </span>
                <span className="text-[10px] font-semibold text-blue-300 tracking-wider uppercase block">
                  Tratamiento de Agua
                </span>
              </div>
            </NavLink>

            <nav aria-label="Principal" className="flex flex-wrap items-center gap-1.5 text-xs font-medium">
              {ENLACES.filter((l) => user && l.roles.includes(user.rol)).map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) =>
                    isActive
                      ? "flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-1.5 font-bold text-white shadow-xs shadow-blue-500/30 transition-all scale-102"
                      : "flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
                  }
                >
                  <Icono id={l.icon} className="h-3.5 w-3.5" />
                  <span>{l.texto}</span>
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-2 rounded-xl bg-white/10 border border-white/15 px-3 py-1.5">
              <div className="h-6 w-6 rounded-full bg-blue-500/30 flex items-center justify-center font-bold text-blue-200 uppercase text-[11px] border border-blue-400/30">
                {user?.nombre?.charAt(0) || "U"}
              </div>
              <span className="font-semibold text-white/95">{user?.nombre}</span>
              <span className="rounded-full bg-blue-500/20 border border-blue-400/30 px-2 py-0.5 text-[10px] font-bold tracking-wider text-blue-200">
                {user?.rol}
              </span>
            </div>

            <button
              type="button"
              onClick={logout}
              className="rounded-xl border border-white/20 bg-white/5 hover:bg-red-500/20 hover:border-red-400/40 px-3 py-1.5 font-semibold text-white/80 hover:text-white transition-all cursor-pointer"
            >
              Salir
            </button>
          </div>
        </header>

        {/* Barra de migas de pan y contexto del módulo */}
        <div className="bg-white border-b border-slate-200/80 px-6 py-2.5 shadow-2xs">
          <div className="mx-auto max-w-6xl flex items-center justify-between text-xs text-slate-500 font-medium">
            <div className="flex items-center gap-2">
              <NavLink to="/clientes" className="hover:text-blue-600 transition-colors">
                Plataforma
              </NavLink>
              <span>/</span>
              <span className="text-slate-800 font-bold">{seccionActual?.texto || "Inicio"}</span>
            </div>
            <span className="text-[11px] text-slate-400">Fildlab Perú S.A.C. · Trujillo</span>
          </div>
        </div>

        <main className="mx-auto max-w-6xl p-5">
          <Outlet />
        </main>
      </div>

      <footer className="mt-12 border-t border-slate-200 bg-white py-4 px-6 text-center text-xs text-slate-400">
        <p>Sistema de Gestión Integral de Tratamiento de Agua · Fildlab Perú S.A.C.</p>
      </footer>
    </div>
  );
}
