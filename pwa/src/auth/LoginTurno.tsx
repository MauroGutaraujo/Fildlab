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
    <main className="mx-auto mt-12 max-w-sm rounded-2xl bg-white p-7 shadow-xl border border-slate-100">
      <div className="mb-6 flex flex-col items-center text-center">
        <img src="/logo.png" alt="Fildlab Campo" className="mb-3 h-20 w-20 rounded-3xl shadow-lg border border-slate-100 object-contain" />
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">Fildlab Campo</h1>
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
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all"
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
            className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all"
          />
        </label>
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 p-2.5 text-xs font-medium text-red-700 border border-red-200">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={enviando}
          className="w-full rounded-xl bg-gradient-to-r from-blue-600 via-blue-600 to-sky-500 py-3 text-sm font-semibold text-white shadow-md hover:from-blue-700 hover:to-sky-600 transition-all active:scale-[0.99] disabled:opacity-60 cursor-pointer"
        >
          {enviando ? "Iniciando Turno…" : "Iniciar Turno de Campo"}
        </button>
      </form>
    </main>
  );
}
