import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
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
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 flex items-center justify-center px-4 py-10">
      <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-blue-500/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -right-16 h-80 w-80 rounded-full bg-indigo-500/20 blur-3xl" />

      <main className="relative w-full max-w-sm rounded-3xl bg-white/95 backdrop-blur p-8 shadow-2xl shadow-black/30 border border-white/40">
        <div className="mb-6 flex flex-col items-center text-center">
          <img src="/logo.png" alt="Fildlab" className="mb-3 h-16 w-16 rounded-2xl shadow-md border border-slate-100 object-contain" />
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-800">Fildlab</h1>
          <h2 className="text-sm font-semibold text-blue-700">Ingreso a la Plataforma</h2>
          <p className="text-xs font-medium text-slate-500">Plataforma Administrativa de Tratamiento de Agua</p>
        </div>
        <form onSubmit={enviar} className="space-y-4">
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
            Correo Electrónico
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
              placeholder="ejemplo@fildlab.pe"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-sm focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 outline-none transition-all"
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
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-sm focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 outline-none transition-all"
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
            className="w-full rounded-xl bg-gradient-to-r from-sky-600 to-blue-700 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-950/20 hover:brightness-110 transition-all active:scale-[0.99] disabled:opacity-60 cursor-pointer"
          >
            {enviando ? "Ingresando…" : "Ingresar a la Plataforma"}
          </button>
        </form>
      </main>
    </div>
  );
}
