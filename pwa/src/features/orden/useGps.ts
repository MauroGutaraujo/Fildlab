import { useCallback, useState } from "react";

type EstadoGps = { lat: number | null; lng: number | null; error: string | null };

export function useGps() {
  const [estado, setEstado] = useState<EstadoGps>({ lat: null, lng: null, error: null });

  const solicitar = useCallback(() => {
    const geo = (navigator as Partial<Navigator>).geolocation;
    if (!geo) {
      setEstado({ lat: null, lng: null, error: "Geolocalización no disponible en este dispositivo" });
      return;
    }
    geo.getCurrentPosition(
      (pos) => setEstado({ lat: pos.coords.latitude, lng: pos.coords.longitude, error: null }),
      (err) => {
        const mensaje =
          err.code === 1
            ? "Se necesita permiso de ubicación para cerrar la orden"
            : "No se pudo obtener la ubicación. Intenta de nuevo";
        setEstado({ lat: null, lng: null, error: mensaje });
      },
    );
  }, []);

  return { ...estado, solicitar };
}
