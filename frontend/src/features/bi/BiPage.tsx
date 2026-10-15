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
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">Analítica de servicio</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">Business Intelligence</h1>
          <p className="mt-1 text-sm text-slate-500">Cumplimiento de SLA y rentabilidad contractual.</p>
        </div>
        <label className="text-sm font-medium text-slate-700">
          Periodo
          <input
            type="month"
            aria-label="Periodo"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
      </div>
      <div className="grid gap-5">
        <TableroRentabilidad periodo={periodo} />
        <TableroSla periodo={periodo} />
      </div>
    </section>
  );
}
