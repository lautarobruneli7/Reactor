import type { ReactNode } from 'react';
import type { Compuesto } from '../../types';

/** Categorías de la biblioteca, en el mismo orden que el backend (GET /api/categorias). */
export const CATEGORIAS = [
  'Principios activos',
  'Orgánicos',
  'Solventes',
  'Ácidos',
  'Bases',
  'Sales y óxidos',
  'Gases',
  'Elementos',
  'Catalizadores',
  'Excipientes',
] as const;
export type Categoria = (typeof CATEGORIAS)[number];

export const categoriaDe = (c: Compuesto): string => c.categoria;

/** "C10H14" → C₁₀H₁₄ (con subíndices reales); también "CuSO4·5H2O" y "Ca(OH)2". */
export function Formula({ texto }: { texto: string | null }): ReactNode {
  if (!texto) return null;
  // solo son subíndices los números que siguen a una letra o a un paréntesis ("5H2O" conserva el 5 normal)
  return texto.split(/((?<=[A-Za-z)\]])\d+)/).map((p, i) => (i % 2 ? <sub key={i}>{p}</sub> : p));
}

/** Minúsculas y sin acentos, para que "acido" encuentre "Ácido". */
export const normalizar = (t: string): string =>
  t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

/** Filtra por categoría y por texto (nombre, fórmula, CAS y sinónimos; cada palabra debe aparecer). */
export function filtrar(compuestos: Compuesto[], busqueda: string, categoria: string): Compuesto[] {
  const palabras = normalizar(busqueda).split(/\s+/).filter(Boolean);
  return compuestos.filter((c) => {
    if (categoria !== 'todas' && c.categoria !== categoria) return false;
    if (palabras.length === 0) return true;
    const pajar = normalizar([c.nombre, c.formula ?? '', c.cas ?? '', ...c.sinonimos].join(' '));
    return palabras.every((p) => pajar.includes(p));
  });
}
