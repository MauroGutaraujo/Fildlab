import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api/client";
import { clearToken, getToken, setToken } from "./session";

export type Rol = "GERENCIA" | "TECNICO";
export type Usuario = { id: number; nombre: string; email: string; rol: Rol };

export type AuthValue = {
  user: Usuario | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthValue | null>(null);

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [loading, setLoading] = useState<boolean>(() => getToken() !== null);

  useEffect(() => {
    if (getToken() === null) return;
    let vivo = true;
    apiFetch<Usuario>("/auth/me")
      .then((u) => vivo && setUser(u))
      .catch(() => {
        clearToken();
        if (vivo) setUser(null);
      })
      .finally(() => vivo && setLoading(false));
    return () => {
      vivo = false;
    };
  }, []);

  useEffect(() => {
    const alExpirar = () => setUser(null);
    window.addEventListener("auth:unauthorized", alExpirar);
    return () => window.removeEventListener("auth:unauthorized", alExpirar);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiFetch<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setToken(access_token);
    try {
      setUser(await apiFetch<Usuario>("/auth/me"));
    } catch (e) {
      clearToken();
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
