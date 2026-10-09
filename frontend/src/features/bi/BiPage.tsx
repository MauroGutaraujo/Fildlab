import { useState } from "react";
import { TableroRentabilidad } from "./TableroRentabilidad";
import { TableroSla } from "./TableroSla";

// "Mes calendario" es el mes del negocio (Trujillo, Peru, UTC-5) — no UTC. Usamos Intl con
// timeZone explicito en vez de los componentes locales del navegador, para que el resultado
// no dependa de en que huso horario este configurado el dispositivo que abre la pagina.
export function periodoActual(): string {
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Lima",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const anio = partes.find((p) => p.type === "year")!.value;
  const mes = partes.find((p) => p.type === "month")!.value;
  return `${anio}-${mes}`;
}

export function BiPage() {
  const [periodo, setPeriodo] = useState(periodoActual());

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Business Intelligence</h1>
        <label className="text-sm font-medium text-slate-700">
          Periodo
          <input
            type="month"
            aria-label="Periodo"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="ml-2 rounded border border-slate-300 px-2 py-1"
          />
        </label>
      </div>
      <div className="grid gap-6">
        <TableroRentabilidad periodo={periodo} />
        <TableroSla periodo={periodo} />
      </div>
    </section>
  );
}
