import type { ComponenteEnReactor, ComponenteGuardado, Resultado } from '../types';

/**
 * Gramos de material de un componente. Con unidad "g" es la cantidad; con otra unidad (mL, mol...)
 * los convierte el backend (necesita densidad o peso molecular), así que se toman de `resultado.cargas`.
 */
export function gramosDe(x: Pick<ComponenteEnReactor, 'id' | 'cantidad' | 'unidad'>, resultado: Resultado | null): number {
  if (x.unidad === 'g') return x.cantidad;
  const c = resultado?.cargas.find((k) => k.id === x.id);
  if (c) return c.gramos_material;
  if (x.unidad === 'kg') return x.cantidad * 1000;
  if (x.unidad === 'mg') return x.cantidad / 1000;
  return 0;
}

/** "78, 82 ; 80" → [78, 82, 80]. Ignora lo que no es un número entre 0 y 100. */
export function parsearRendimiento(texto: string): number[] {
  return texto
    .split(/[\s,;]+/)
    .filter(Boolean)
    .map((t) => Number(t.replace(',', '.')))
    .filter((v) => Number.isFinite(v) && v >= 0 && v <= 100);
}

/** Los ensayos guardados antes de las unidades traían `gramos`: se leen como cantidad en gramos. */
export function aComponenteGuardado(x: Partial<ComponenteGuardado> & { id: string; gramos?: number; pureza?: number }): ComponenteGuardado {
  return {
    id: x.id,
    cantidad: x.cantidad ?? x.gramos ?? 0,
    unidad: x.unidad ?? 'g',
    pureza: x.pureza ?? 100,
    concentracion: x.concentracion ?? null,
    densidad: x.densidad ?? null,
  };
}

/** Texto corto de una cantidad: "36,5 g", "2 mol". */
export function textoCantidad(cantidad: number, unidad: string): string {
  const n = Math.abs(cantidad) >= 100 ? cantidad.toFixed(0) : Number(cantidad.toPrecision(4)).toString();
  return `${n} ${unidad}`;
}
