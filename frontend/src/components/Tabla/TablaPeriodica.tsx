import { useEffect, useMemo, useState } from 'react';
import { obtenerElementos } from '../../api/client';
import type { Elemento } from '../../types';
import { normalizar } from '../Compuestos/categorias';

const COLOR_CATEGORIA: Record<string, string> = {
  'no metal': 'rgba(46, 230, 197, .55)',
  'gas noble': 'rgba(182, 140, 255, .6)',
  'metal alcalino': 'rgba(255, 107, 129, .6)',
  'metal alcalinotérreo': 'rgba(251, 176, 64, .6)',
  metaloide: 'rgba(125, 211, 130, .55)',
  halógeno: 'rgba(77, 208, 255, .6)',
  'metal postransicional': 'rgba(138, 160, 196, .6)',
  'metal de transición': 'rgba(255, 180, 84, .45)',
  lantánido: 'rgba(255, 143, 171, .55)',
  actínido: 'rgba(255, 94, 200, .5)',
};

const slug = (categoria: string) => normalizar(categoria).replace(/\s+/g, '-');

/** Columna y fila de la cuadrícula: lantánidos y actínidos van en dos filas aparte, debajo del cuerpo principal. */
function posicion(e: Elemento): { col: number; fila: number } {
  if (e.grupo !== null) return { col: e.grupo, fila: e.periodo };
  if (e.numero >= 57 && e.numero <= 71) return { col: e.numero - 57 + 3, fila: 9 };
  return { col: e.numero - 89 + 3, fila: 10 };
}

function Detalle({ e }: { e: Elemento }) {
  return (
    <aside className="panel detalle" aria-live="polite">
      <div className="detalle-cabecera">
        <span className="mono" style={{ fontSize: 44, fontWeight: 700, color: 'var(--acento)' }}>{e.simbolo}</span>
        <div>
          <h2 className="titulo-panel grande">{e.nombre}</h2>
          <div className="nota">{e.nombre_en} · {e.categoria}</div>
        </div>
      </div>
      <table className="tabla">
        <tbody>
          <tr><td>Número atómico</td><td className="mono">{e.numero}</td></tr>
          <tr><td>Masa atómica</td><td className="mono">{e.masa_atomica} g/mol</td></tr>
          <tr><td>Grupo</td><td className="mono">{e.grupo ?? '—'}</td></tr>
          <tr><td>Período</td><td className="mono">{e.periodo}</td></tr>
          <tr><td>Fase a 25 °C</td><td>{e.fase_25c ?? 'sin dato'}</td></tr>
          <tr><td>Radiactivo</td><td>{e.radiactivo ? 'Sí' : 'No'}</td></tr>
        </tbody>
      </table>
      {e.radiactivo && (
        <p className="nota">
          Sin isótopo estable: la masa es la del isótopo más estable conocido. Los elementos radiactivos figuran acá para poder calcular fórmulas, pero no se ofrecen como sustancias.
        </p>
      )}
      <p className="nota">Fuente: {e.fuente}</p>
    </aside>
  );
}

/** Tabla periódica de los 118 elementos (datos NIST del backend). */
export function TablaPeriodica() {
  const [elementos, setElementos] = useState<Elemento[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [elegido, setElegido] = useState<number | null>(null);
  const [categoria, setCategoria] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');

  useEffect(() => {
    obtenerElementos()
      .then(setElementos)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Error desconocido'));
  }, []);

  const categorias = useMemo(() => [...new Set(elementos.map((e) => e.categoria))], [elementos]);
  const q = normalizar(busqueda);
  const coincide = (e: Elemento) =>
    q === '' || [e.simbolo, e.nombre, e.nombre_en, String(e.numero)].some((t) => normalizar(t).includes(q));
  const detalle = elementos.find((e) => e.numero === elegido) ?? null;

  return (
    <div className="vista-tabla">
      <section className="panel">
        <div className="panel-cabecera">
          <h2 className="titulo-panel grande">Tabla periódica</h2>
          <input
            className="campo"
            style={{ maxWidth: 260 }}
            type="search"
            placeholder="Buscar símbolo, nombre o número"
            aria-label="Buscar elemento"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>

        {error && <div className="alerta bad">No se pudo cargar la tabla: {error}</div>}

        <div className="leyenda">
          {categorias.map((c) => (
            <button key={c} className={categoria === c ? 'on' : ''} aria-pressed={categoria === c} onClick={() => setCategoria(categoria === c ? null : c)}>
              <i style={{ background: COLOR_CATEGORIA[c] ?? 'var(--tenue)' }} />
              {c}
            </button>
          ))}
        </div>

        <div className="periodica" role="grid" aria-label="Tabla periódica de los elementos">
          {elementos.map((e) => {
            const { col, fila } = posicion(e);
            const activo = coincide(e) && (categoria === null || e.categoria === categoria);
            return (
              <button
                key={e.numero}
                className={`elemento cat-${slug(e.categoria)}${elegido === e.numero ? ' elegido' : ''}${activo ? '' : ' atenuado'}`}
                style={{ gridColumn: col, gridRow: fila }}
                aria-label={`${e.nombre} (${e.simbolo}), número ${e.numero}`}
                aria-pressed={elegido === e.numero}
                onClick={() => setElegido(e.numero)}
              >
                <span className="num">{e.numero}</span>
                <span className="sim">{e.simbolo}</span>
                <span className="masa">{e.masa_atomica.toFixed(e.masa_atomica >= 100 ? 1 : 2)}</span>
              </button>
            );
          })}
          {elementos.length > 0 && (
            <>
              <div className="marcador-serie" style={{ gridColumn: 3, gridRow: 6 }}>57–71</div>
              <div className="marcador-serie" style={{ gridColumn: 3, gridRow: 7 }}>89–103</div>
            </>
          )}
        </div>
        {elementos.length === 0 && !error && <p className="nota">Cargando…</p>}
      </section>

      {detalle ? <Detalle e={detalle} /> : <aside className="panel detalle"><p className="vacio">Elegí un elemento para ver su detalle.</p></aside>}
    </div>
  );
}
