import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Rol, useAuth } from "../auth/AuthContext";

type IconoId = "clientes" | "contratos" | "equipos" | "inventario" | "ventas" | "liquidacion" | "bi";

const ICONOS: Record<IconoId, string> = {
  clientes: "M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6M9 10h.01M15 10h.01M9 14h.01M15 14h.01",
  contratos: "M7 3h8l4 4v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1zM9 9h6M9 13h6M9 17h4",
  equipos: "M12 3s6 6.5 6 11a6 6 0 11-12 0c0-4.5 6-11 6-11z",
  inventario: "M4 7l8-4 8 4-8 4-8-4zm0 0v10l8 4m0-14v14m8-14v10l-8 4",
  ventas: "M4 8h16v11a1 1 0 01-1 1H5a1 1 0 01-1-1V8zm2 0V6a2 2 0 012-2h8a2 2 0 012 2v2",
  liquidacion: "M12 3v18M6 7l-3 6a3 3 0 006 0l-3-6zm12 0l-3 6a3 3 0 006 0l-3-6zM3 7h6m6 0h6",
  bi: "M4 19V9m6 10V5m6 14v-7",
};

function Icono({ id, className }: { id: IconoId; className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
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
  { to: "/bi", texto: "BI", icon: "bi", roles: ["GERENCIA"] },
];

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const seccionActual = ENLACES.find((e) => location.pathname.startsWith(e.to));

  return (
    <div className="min-h-screen bg-slate-100 selection:bg-sky-100 selection:text-sky-950 lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
      <aside
        aria-label="Navegación administrativa"
        className="sticky top-0 z-30 border-b border-slate-200 bg-white px-4 py-3 shadow-sm lg:flex lg:h-screen lg:flex-col lg:border-b-0 lg:border-r lg:px-5 lg:py-6 lg:shadow-none"
      >
        <NavLink to="/clientes" className="flex w-fit items-center gap-3 rounded-xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600">
          <img src="/logo.png" alt="Fildlab" className="h-10 w-10 rounded-xl border border-slate-200 bg-white object-contain p-1" />
          <span className="leading-tight">
            <span className="block text-lg font-extrabold tracking-tight text-slate-950">Fildlab</span>
            <span className="block text-[10px] font-semibold uppercase tracking-[0.16em] text-sky-700">Tratamiento de agua</span>
          </span>
        </NavLink>

        <nav aria-label="Principal" className="mt-4 flex gap-1.5 overflow-x-auto pb-1 text-sm lg:mt-10 lg:flex-col lg:overflow-visible">
          <p className="hidden px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400 lg:block">Operación</p>
          {ENLACES.filter((l) => user && l.roles.includes(user.rol)).map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                isActive
                  ? "flex shrink-0 items-center gap-3 rounded-xl bg-blue-50 px-3 py-2.5 font-semibold text-blue-800 ring-1 ring-inset ring-blue-100 lg:w-full"
                  : "flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950 lg:w-full"
              }
            >
              <Icono id={l.icon} className="h-[18px] w-[18px] shrink-0" />
              <span>{l.texto}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-3 hidden items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 lg:mt-auto lg:flex">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-900">
            {user?.nombre?.charAt(0) || "U"}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">{user?.nombre}</p>
            <p className="text-xs text-slate-500">{user?.rol}</p>
          </div>
        </div>
      </aside>

      <div className="flex min-h-screen min-w-0 flex-col">
        <header className="flex min-h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 sm:px-6 lg:px-8">
          <div className="min-w-0">
            <p className="text-xs font-medium text-slate-500">Plataforma / {seccionActual?.texto || "Inicio"}</p>
            <p className="truncate text-sm font-semibold text-slate-900">Fildlab Perú S.A.C. · Trujillo</p>
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <span className="hidden text-sm font-medium text-slate-600 sm:inline">{user?.nombre}</span>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              Salir
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[96rem] flex-1 p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>

        <footer className="border-t border-slate-200 bg-white px-6 py-4 text-center text-xs text-slate-500">
          <p>Sistema de Gestión Integral de Tratamiento de Agua · Fildlab Perú S.A.C.</p>
        </footer>
      </div>
    </div>
  );
}
