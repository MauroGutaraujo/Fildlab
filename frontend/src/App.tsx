import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./auth/LoginPage";
import { RequireRole } from "./auth/RequireRole";
import { Layout } from "./components/Layout";
import { BiPage } from "./features/bi/BiPage";
import { ClientesPage } from "./features/clientes/ClientesPage";
import { ContratosPage } from "./features/contratos/ContratosPage";
import { EquiposPage } from "./features/equipos/EquiposPage";
import { InventarioPage } from "./features/inventario/InventarioPage";
import { LiquidacionPage } from "./features/liquidacion/LiquidacionPage";
import { VentasPage } from "./features/ventas/VentasPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireRole roles={["GERENCIA", "TECNICO"]}>
            <Layout />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="/clientes" replace />} />
        <Route path="clientes" element={<ClientesPage />} />
        <Route path="contratos" element={<ContratosPage />} />
        <Route path="equipos" element={<EquiposPage />} />
        <Route path="inventario" element={<InventarioPage />} />
        <Route
          path="ventas"
          element={
            <RequireRole roles={["GERENCIA"]}>
              <VentasPage />
            </RequireRole>
          }
        />
        <Route
          path="liquidacion"
          element={
            <RequireRole roles={["GERENCIA"]}>
              <LiquidacionPage />
            </RequireRole>
          }
        />
        <Route
          path="bi"
          element={
            <RequireRole roles={["GERENCIA"]}>
              <BiPage />
            </RequireRole>
          }
        />
        <Route path="*" element={<p className="p-6">Página no encontrada</p>} />
      </Route>
    </Routes>
  );
}
