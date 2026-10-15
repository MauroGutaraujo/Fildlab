import type { CampoLectura } from "../../lib/validators";

type Lecturas = Record<CampoLectura, string>;
type Props = {
  lecturas: Lecturas;
  tocado: Partial<Record<CampoLectura, boolean>>;
  errores: Record<CampoLectura, string | null>;
  onValor: (campo: CampoLectura, valor: string) => void;
  onTocado: (campo: CampoLectura) => void;
};

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

const GRUPOS: { titulo: string; campos: CampoLectura[] }[] = [
  {
    titulo: "Calidad del agua",
    campos: ["tds_entrada_ppm", "tds_post_membrana_ppm", "tds_producto_final_ppm", "ph", "conductividad_us_cm", "resistividad_mohm_cm"],
  },
  { titulo: "Producción y consumo", campos: ["litros_consumidos_red", "litros_agua_pura"] },
];

export function LecturasAguaFields({ lecturas, tocado, errores, onValor, onTocado }: Props) {
  return (
    <div className="space-y-4">
      {GRUPOS.map((grupo) => (
        <fieldset key={grupo.titulo} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <legend className="px-1 text-sm font-bold text-slate-900">{grupo.titulo}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {grupo.campos.map((campo) => {
              const errorId = `${campo}-error`;
              const error = errores[campo];
              return (
                <label key={campo} htmlFor={campo} className="block text-sm font-medium text-slate-700">
                  {ETIQUETAS[campo]}
                  <input
                    id={campo}
                    value={lecturas[campo]}
                    onChange={(e) => onValor(campo, e.target.value)}
                    onBlur={() => onTocado(campo)}
                    inputMode="decimal"
                    aria-invalid={tocado[campo] && error ? true : undefined}
                    aria-describedby={tocado[campo] && error ? errorId : undefined}
                    className="mt-1.5 min-h-12 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-3 text-base text-slate-950 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 aria-[invalid=true]:border-rose-400 aria-[invalid=true]:focus:ring-rose-100"
                  />
                  {tocado[campo] && error && <span id={errorId} className="mt-1 block text-sm font-medium text-rose-700">{error}</span>}
                </label>
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
