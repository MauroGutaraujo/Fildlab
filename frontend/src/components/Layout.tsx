import { NavLink, Outlet } from "react-router-dom";
import { Rol, useAuth } from "../auth/AuthContext";

const ENLACES: { to: string; texto: string; roles: Rol[] }[] = [
  { to: "/clientes", texto: "Clientes", roles: ["GERENCIA", "TECNICO"] },
  { to: "/contratos", texto: "Contratos", roles: ["GERENCIA", "TECNICO"] },
  { to: "/equipos", texto: "Equipos", roles: ["GERENCIA", "TECNICO"] },
  { to: "/inventario", texto: "Inventario", roles: ["GERENCIA", "TECNICO"] },
  { to: "/ventas", texto: "Ventas", roles: ["GERENCIA"] },
  { to: "/liquidacion", texto: "Liquidación", roles: ["GERENCIA"] },
];

export function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex flex-wrap items-center justify-between gap-3 bg-gradient-to-r from-blue-700 via-blue-600 to-sky-500 px-4 py-2.5 text-white shadow-md">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <img src="/logo.png" alt="Fildlab" className="h-9 w-9 rounded-xl shadow-sm border border-white/20 object-contain bg-white/10" />
            <span className="text-xl font-bold tracking-tight text-white drop-shadow-sm">Fildlab</span>
          </div>
          <nav aria-label="Principal" className="flex flex-wrap gap-4 text-sm font-medium">
            {ENLACES.filter((l) => user && l.roles.includes(user.rol)).map((l) => (
              <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? "rounded-md bg-white/20 px-2.5 py-1 font-semibold text-white shadow-xs" : "rounded-md px-2.5 py-1 text-white/90 hover:bg-white/10 hover:text-white")}>
                {l.texto}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="rounded-full bg-white/15 px-3 py-1 text-xs font-medium tracking-wide">
            {user?.nombre} · {user?.rol}
          </span>
          <button type="button" onClick={logout} className="rounded-md border border-white/40 bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20 transition-colors">
            Salir
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl p-4">
        <Outlet />
      </main>
    </div>
  );
}
