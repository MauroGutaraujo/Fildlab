import { useState } from "react";
import { TableroRentabilidad } from "./TableroRentabilidad";
import { TableroSla } from "./TableroSla";

function periodoActual(): string {
  return new Date().toISOString().slice(0, 7);
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
