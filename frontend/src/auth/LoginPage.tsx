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
    <main className="mx-auto mt-20 max-w-sm rounded-2xl bg-white p-8 shadow-xl border border-slate-100">
      <div className="mb-6 flex flex-col items-center text-center">
        <img src="/logo.png" alt="Fildlab" className="mb-3 h-16 w-16 rounded-2xl shadow-md border border-slate-100 object-contain" />
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">Fildlab</h1>
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
          {enviando ? "Ingresando…" : "Ingresar a la Plataforma"}
        </button>
      </form>
    </main>
  );
}
