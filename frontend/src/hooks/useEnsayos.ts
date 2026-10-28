import { useCallback, useEffect, useState } from 'react';
import type { Ensayo } from '../types';

const CLAVE = 'retorta.ensayos';

function leer(): Ensayo[] {
  try {
    const crudo = localStorage.getItem(CLAVE);
    return crudo ? (JSON.parse(crudo) as Ensayo[]) : [];
  } catch {
    return [];
  }
}

/** Ensayos guardados en el navegador (localStorage). Cuando haya usuarios, esto pasa al backend. */
export function useEnsayos() {
  const [ensayos, setEnsayos] = useState<Ensayo[]>(leer);

  useEffect(() => {
    localStorage.setItem(CLAVE, JSON.stringify(ensayos));
  }, [ensayos]);

  /** Número que tendrá el próximo ensayo guardado. */
  const siguiente = ensayos.reduce((m, e) => Math.max(m, e.numero), 0) + 1;

  const guardar = useCallback((e: Omit<Ensayo, 'numero' | 'fecha'>) => {
    setEnsayos((prev) => {
      const numero = prev.reduce((m, x) => Math.max(m, x.numero), 0) + 1;
      return [{ ...e, numero, fecha: new Date().toISOString() }, ...prev];
    });
  }, []);

  const eliminar = useCallback((numero: number) => setEnsayos((prev) => prev.filter((e) => e.numero !== numero)), []);

  return { ensayos, siguiente, guardar, eliminar };
}
