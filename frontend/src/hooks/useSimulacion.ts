import { useEffect, useState } from 'react';
import { simular } from '../api/client';
import type { ComponenteEnReactor, Medidos, OpcionesIncertidumbre, SimulacionSalida } from '../types';

/**
 * Llama al backend cada vez que cambia la mezcla (con un pequeño retardo para
 * no disparar un pedido por cada pixel que se mueve un slider). Con la incertidumbre
 * activada el retardo es mayor: cada pedido corre cientos de simulaciones.
 */
export function useSimulacion(
  componentes: ComponenteEnReactor[],
  reaccionId: string,
  medidos: Medidos,
  incertidumbre: OpcionesIncertidumbre,
) {
  const [salida, setSalida] = useState<SimulacionSalida | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (componentes.length === 0) {
      setSalida(null);
      setError(null);
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      setCargando(true);
      simular({ componentes, reaccionId, medidos, incertidumbre }, ctrl.signal)
        .then((s) => {
          setSalida(s);
          setError(null);
        })
        .catch((e: unknown) => {
          if (e instanceof DOMException && e.name === 'AbortError') return;
          setSalida(null);
          setError(e instanceof Error ? e.message : 'Error desconocido');
        })
        .finally(() => setCargando(false));
    }, incertidumbre.activa ? 400 : 150);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [componentes, reaccionId, medidos, incertidumbre]);

  return { salida, error, cargando };
}
