import { useEffect, useState } from "react";
import { decodeTecnicoId, obtenerToken } from "./auth/session";
import { LoginTurno } from "./auth/LoginTurno";
import { buscarEquipos, refrescarCatalogo } from "./db/catalogo";
import type { CatalogoItem } from "./db/dexie";
import { OrdenForm } from "./features/orden/OrdenForm";
import { StockMovil } from "./features/stock/StockMovil";

type EquipoDatos = { serie: string; contrato_id: number };

function EquipoPicker({ onElegido }: { onElegido: (equipo: EquipoDatos) => void }) {
  const [query, setQuery] = useState("");
  const [equipos, setEquipos] = useState<CatalogoItem[]>([]);

  useEffect(() => {
    refrescarCatalogo().finally(() => buscarEquipos("").then(setEquipos));
  }, []);

  useEffect(() => {
    buscarEquipos(query).then(setEquipos);
  }, [query]);

  return (
    <section className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Elegir equipo</h1>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Buscar por serie…"
        className="mb-3 w-full rounded border border-slate-300 px-3 py-2"
      />
      <ul className="space-y-1">
        {equipos.map((e) => (
          <li key={e.id}>
            <button
              type="button"
              onClick={() => onElegido(e.datos as EquipoDatos)}
              className="w-full rounded border border-slate-200 px-3 py-2 text-left hover:bg-slate-50"
            >
              {e.id}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function App() {
  const [token, setToken] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [equipo, setEquipo] = useState<EquipoDatos | null>(null);
  const [pantalla, setPantalla] = useState<"equipo" | "orden" | "stock">("equipo");

  useEffect(() => {
    obtenerToken()
      .then(setToken)
      .finally(() => setCargando(false));
  }, []);

  if (cargando) return <p className="p-6 text-slate-500">Cargando…</p>;
  if (!token) return <LoginTurno onIngreso={() => obtenerToken().then(setToken)} />;

  const tecnicoId = decodeTecnicoId(token);

  if (pantalla === "stock") return <StockMovil />;
  if (pantalla === "orden" && equipo && tecnicoId !== null) {
    return (
      <OrdenForm
        contratoId={equipo.contrato_id}
        equipoSerie={equipo.serie}
        tecnicoId={tecnicoId}
        onCerrada={() => {
          setEquipo(null);
          setPantalla("equipo");
        }}
      />
    );
  }
  return (
    <>
      <nav className="flex justify-end gap-3 p-2 text-sm">
        <button type="button" onClick={() => setPantalla("stock")} className="text-sky-700 hover:underline">
          Stock móvil
        </button>
      </nav>
      <EquipoPicker
        onElegido={(e) => {
          setEquipo(e);
          setPantalla("orden");
        }}
      />
    </>
  );
}
