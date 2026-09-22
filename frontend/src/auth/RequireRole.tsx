import { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { Rol, useAuth } from "./AuthContext";

/** Protege una ruta por rol. El backend sigue siendo la autoridad (RN-01); esto solo evita mostrar pantallas inútiles. */
export function RequireRole({ roles, children }: { roles: Rol[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="p-6 text-slate-500">Cargando…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.rol)) {
    return (
      <div role="alert" className="m-6 rounded border border-red-200 bg-red-50 p-4 text-red-800">
        <strong>Acceso denegado.</strong> Tu rol ({user.rol}) no tiene permiso para esta sección.
      </div>
    );
  }
  return <>{children}</>;
}
