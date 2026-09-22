import { useRef } from "react";
import SignatureCanvas from "react-signature-canvas";

/** DPR=2 fijo: el trazo no escala con window.devicePixelRatio del dispositivo, para que
 * el payload de firma pese lo mismo en cualquier Galaxy A14 (spec 3.2, sección 3.4). */
export function Firma({ onCambio }: { onCambio: (base64: string | null) => void }) {
  const ref = useRef<SignatureCanvas>(null);

  return (
    <div>
      <SignatureCanvas
        canvasProps={
          {
            "data-testid": "firma-canvas",
            className: "w-full rounded border border-slate-300 bg-white",
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
        className="mt-1 text-sm text-sky-700 hover:underline"
      >
        Limpiar firma
      </button>
    </div>
  );
}
