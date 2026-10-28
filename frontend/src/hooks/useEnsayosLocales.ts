import { useCallback, useState } from 'react';
import type { Ensayo } from '../types';
import { aComponenteGuardado } from '../utilidades/cargas';

const CLAVE = 'retorta.ensayos';

function leer(): Ensayo[] {
  try {
    const crudo = localStorage.getItem(CLAVE);
    if (!crudo) return [];
    return (JSON.parse(crudo) as Ensayo[]).map((e) => ({ ...e, componentes: e.componentes.map(aComponenteGuardado) }));
  } catch {
    return [];
  }
}

/** Ensayos que la versión anterior guardaba en el navegador (localStorage). Solo se leen para importarlos al servidor. */
export function useEnsayosLocales() {
  const [locales, setLocales] = useState<Ensayo[]>(leer);

  /** Deja en el navegador solo los que NO se importaron. */
  const quitar = useCallback((numeros: number[]) => {
    setLocales((prev) => {
      const quedan = prev.filter((e) => !numeros.includes(e.numero));
      try {
        if (quedan.length) localStorage.setItem(CLAVE, JSON.stringify(quedan));
        else localStorage.removeItem(CLAVE);
      } catch {
        /* sin almacenamiento */
      }
      return quedan;
    });
  }, []);

  return { locales, quitar };
}
