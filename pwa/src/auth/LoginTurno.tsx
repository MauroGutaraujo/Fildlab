import { FormEvent, useState } from "react";
import { ApiError, apiFetch } from "../api/client";
import { guardarSesionTurno } from "./session";

export function LoginTurno({ onIngreso }: { onIngreso: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password || enviando) return;
    setEnviando(true);
    setError(null);
    try {
      const { access_token } = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: { email: email.trim(), password, duracion: "turno" },
      });
      await guardarSesionTurno(access_token);
      onIngreso();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-sky-950 via-indigo-950 to-slate-950 flex items-center justify-center px-4 py-10">
      <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-sky-500/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -right-16 h-80 w-80 rounded-full bg-indigo-500/20 blur-3xl" />

      <main className="relative w-full max-w-sm rounded-3xl bg-white/95 backdrop-blur p-7 shadow-2xl shadow-black/30 border border-white/40">
        <div className="mb-6 flex flex-col items-center text-center">
          <img src="/logo.png" alt="Fildlab Campo" className="mb-3 h-20 w-20 rounded-3xl shadow-lg border border-slate-100 object-contain" />
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-800">Fildlab Campo</h1>
          <h2 className="text-sm font-semibold text-sky-700">Ingreso de Turno</h2>
          <p className="text-xs font-medium text-slate-500">PWA Offline · Turno Técnico de 12 Horas</p>
        </div>
        <form onSubmit={enviar} className="space-y-4">
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
            Correo Técnico
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
              placeholder="tecnico@fildlab.pe"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-sm focus:border-sky-500 focus:bg-white focus:ring-4 focus:ring-sky-500/10 outline-none transition-all"
            />
          </label>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
            Contraseña
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="••••••••••••"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-sm focus:border-sky-500 focus:bg-white focus:ring-4 focus:ring-sky-500/10 outline-none transition-all"
            />
          </label>
          {error && (
            <p role="alert" className="rounded-xl bg-red-50 p-2.5 text-xs font-medium text-red-700 border border-red-200">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={enviando}
            aria-label="Ingresar turno"
            className="w-full rounded-xl bg-gradient-to-r from-sky-900 to-indigo-950 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 hover:brightness-110 transition-all active:scale-[0.99] disabled:opacity-60 cursor-pointer"
          >
            {enviando ? "Iniciando Turno…" : "Ingresar / Iniciar Turno"}
          </button>
        </form>
      </main>
    </div>
  );
}
