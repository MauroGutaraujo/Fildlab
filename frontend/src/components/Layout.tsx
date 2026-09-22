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
    <div className="min-h-screen">
      <header className="flex flex-wrap items-center justify-between gap-2 bg-sky-900 px-4 py-3 text-white">
        <nav aria-label="Principal" className="flex flex-wrap gap-4">
          {ENLACES.filter((l) => user && l.roles.includes(user.rol)).map((l) => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? "font-semibold underline" : "hover:underline")}>
              {l.texto}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-3 text-sm">
          <span>
            {user?.nombre} · {user?.rol}
          </span>
          <button type="button" onClick={logout} className="rounded border border-white/60 px-3 py-1">
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
