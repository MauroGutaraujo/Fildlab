import { useState } from "react";
import { CAMPOS_LECTURA_ORDEN, type CampoLectura, errorLectura } from "../../lib/validators";

const ETIQUETAS: Record<CampoLectura, string> = {
  tds_entrada_ppm: "TDS entrada (ppm)",
  tds_post_membrana_ppm: "TDS post-membrana (ppm)",
  tds_producto_final_ppm: "TDS producto final (ppm)",
  ph: "pH",
  conductividad_us_cm: "Conductividad (µS/cm)",
  resistividad_mohm_cm: "Resistividad (MΩ·cm)",
  litros_consumidos_red: "Litros consumidos de red",
  litros_agua_pura: "Litros de agua pura",
};

type Lecturas = Record<CampoLectura, string>;
const vacias = (): Lecturas =>
  Object.fromEntries(CAMPOS_LECTURA_ORDEN.map((c) => [c, ""])) as Lecturas;

export function OrdenForm() {
  const [lecturas, setLecturas] = useState<Lecturas>(vacias());
  const [tocado, setTocado] = useState<Partial<Record<CampoLectura, boolean>>>({});

  const errores = Object.fromEntries(
    CAMPOS_LECTURA_ORDEN.map((c) => [c, errorLectura(c, lecturas[c])]),
  ) as Record<CampoLectura, string | null>;
  const lecturasCompletas = CAMPOS_LECTURA_ORDEN.every((c) => errores[c] === null);

  return (
    <section className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Lecturas de agua</h1>
      <div className="grid gap-3 sm:grid-cols-2">
        {CAMPOS_LECTURA_ORDEN.map((campo) => (
          <label key={campo} className="block text-sm">
            {ETIQUETAS[campo]}
            <input
              id={campo}
              value={lecturas[campo]}
              onChange={(e) => setLecturas((prev) => ({ ...prev, [campo]: e.target.value }))}
              onBlur={() => setTocado((prev) => ({ ...prev, [campo]: true }))}
              inputMode="decimal"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
            {tocado[campo] && errores[campo] && <p className="mt-1 text-red-700">{errores[campo]}</p>}
          </label>
        ))}
      </div>
      <button type="button" disabled={!lecturasCompletas} className="mt-4 rounded bg-sky-700 px-4 py-2 text-white disabled:opacity-60">
        Continuar
      </button>
    </section>
  );
}
