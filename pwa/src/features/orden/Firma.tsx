import { useRef } from "react";
import SignatureCanvas from "react-signature-canvas";

/** DPR=2 fijo: el trazo no escala con window.devicePixelRatio del dispositivo, para que
 * el payload de firma pese lo mismo en cualquier Galaxy A14 (spec 3.2, sección 3.4). */
export function Firma({ onCambio }: { onCambio: (base64: string | null) => void }) {
  const ref = useRef<SignatureCanvas>(null);

  return (
    <div className="space-y-3">
      <SignatureCanvas
        canvasProps={
          {
            "data-testid": "firma-canvas",
            className: "min-h-40 w-full touch-none rounded-xl border border-slate-200 bg-white shadow-inner",
            // width/height explícitos: sin ambos, react-signature-canvas escala el bitmap con
            // window.devicePixelRatio (_resizeCanvas) y el area dibujable vertical real queda
            // recortada a height/ratio — en un Galaxy A14 (DPR~2.6-3) casi toda la firma se pierde.
            width: 600,
            height: 200,
          } as never
        }
        penColor="black"
        minWidth={1}
        maxWidth={2}
        dotSize={1.5}
        velocityFilterWeight={0.7}
        ref={ref}
        onEnd={() => onCambio(ref.current?.isEmpty() ? null : (ref.current?.toDataURL() ?? null))}
      />
      <button
        type="button"
        onClick={() => {
          ref.current?.clear();
          onCambio(null);
        }}
        className="min-h-11 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
      >
        Limpiar firma
      </button>
    </div>
  );
}
