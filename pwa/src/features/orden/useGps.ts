import { useCallback, useState } from "react";

type EstadoGps = { lat: number | null; lng: number | null; error: string | null; solicitando: boolean };

// Sin timeout explícito, PositionOptions.timeout es Infinity por defecto: dentro de un
// edificio sin fix de GPS, getCurrentPosition nunca llama a ningún callback (Review Focus 4).
const OPCIONES = { timeout: 15_000, maximumAge: 60_000, enableHighAccuracy: true };

export function useGps() {
  const [estado, setEstado] = useState<EstadoGps>({ lat: null, lng: null, error: null, solicitando: false });

  const solicitar = useCallback(() => {
    const geo = (navigator as Partial<Navigator>).geolocation;
    if (!geo) {
      setEstado({ lat: null, lng: null, error: "Geolocalización no disponible en este dispositivo", solicitando: false });
      return;
    }
    setEstado((prev) => ({ ...prev, solicitando: true, error: null }));
    geo.getCurrentPosition(
      (pos) => setEstado({ lat: pos.coords.latitude, lng: pos.coords.longitude, error: null, solicitando: false }),
      (err) => {
        const mensaje =
          err.code === 1
            ? "Se necesita permiso de ubicación para cerrar la orden"
            : "No se pudo obtener la ubicación. Intenta de nuevo";
        setEstado({ lat: null, lng: null, error: mensaje, solicitando: false });
      },
      OPCIONES,
    );
  }, []);

  return { ...estado, solicitar };
}
