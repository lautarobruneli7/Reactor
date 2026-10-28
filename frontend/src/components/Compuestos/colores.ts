/** Color de cada compuesto en la interfaz (mismo criterio que los prototipos 3D). */
export const COLOR_COMPUESTO: Record<string, string> = {
  ibb: '#ffb454',
  aa: '#4dd0ff',
  cat: '#b68cff',
  h2: '#e6f4ff',
  co: '#ff8fab',
  exc: '#fff1c9',
};

/** Color estable para los compuestos que no tienen uno asignado: sale del id, así no cambia entre sesiones. */
function colorDesdeId(id: string): string {
  let h = 0;
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const tono = h % 360;
  // HSL (s 65 %, l 66 %) -> hex
  const a = 0.65 * Math.min(0.66, 1 - 0.66);
  const f = (n: number) => {
    const k = (n + tono / 30) % 12;
    const v = 0.66 - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(v * 255).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

export const colorDe = (id: string): string => COLOR_COMPUESTO[id] ?? colorDesdeId(id);

/** Mismo color como número (para Three.js). */
export const colorNumDe = (id: string): number => parseInt(colorDe(id).slice(1), 16);

/** Color del líquido en el reactor; solo los compuestos líquidos tienen uno. */
const COLOR_LIQUIDO: Record<string, number> = {
  ibb: 0xf59a14,
  aa: 0xffc24d,
};

export const liquidoDe = (id: string): number => COLOR_LIQUIDO[id] ?? 0xf59a14;
