import { useMemo, useState } from 'react';
import type { ComponenteEnReactor, Compuesto, Reaccion, Resultado } from '../../types';
import { gramosDe } from '../../utilidades/cargas';
import { Formula } from '../Compuestos/categorias';
import { colorDe, colorNumDe, liquidoDe } from '../Compuestos/colores';
import { ControlCompuesto, type CambiosComponente } from '../Controles/ControlCompuesto';
import { Escena3D } from './Escena3D';
import type { EstadoEscena } from './motor3d';

interface Props {
  /** Número del ensayo que se está corrigiendo; sin él, la mezcla todavía no se guardó (el servidor asigna el número). */
  numero: number | null;
  componentes: ComponenteEnReactor[];
  catalogo: Compuesto[];
  resultado: Resultado | null;
  reacciones: Reaccion[];
  reaccion: Reaccion | null;
  onReaccion: (id: string) => void;
  onAgregar: (id: string) => void;
  onCambiar: (uid: number, cambios: CambiosComponente) => void;
  onQuitar: (uid: number) => void;
  onEjemplo: () => void;
  onVaciar: () => void;
}

/** Columna central: el reactor 3D (zona para soltar compuestos) y la carga con sus controles. */
export function Reactor({ numero, componentes, catalogo, resultado, reacciones, reaccion, onReaccion, onAgregar, onCambiar, onQuitar, onEjemplo, onVaciar }: Props) {
  const [arrastrando, setArrastrando] = useState(false);
  const [giro, setGiro] = useState(true);
  const [vistaKey, setVistaKey] = useState(0);
  const porId = useMemo(() => new Map(catalogo.map((c) => [c.id, c])), [catalogo]);

  const estado = useMemo<EstadoEscena>(
    () => ({
      items: componentes.flatMap((x) => {
        const c = porId.get(x.id);
        return c
          ? [{ id: x.id, gramos: gramosDe(x, resultado), pm: c.pm, fase: c.fase, color: colorNumDe(x.id), liquido: liquidoDe(x.id) }]
          : [];
      }),
      resultado,
    }),
    [componentes, porId, resultado],
  );

  const gramos = componentes.map((x) => ({ x, g: gramosDe(x, resultado) }));
  const total = gramos.reduce((s, { g }) => s + g, 0);
  const totalTexto = Number(total.toPrecision(5)).toString();

  return (
    <div className="columna">
      <section
        className={`panel${arrastrando ? ' sobre' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          onAgregar(e.dataTransfer.getData('text/plain'));
        }}
      >
        <div className="panel-cabecera">
          <h2 className="titulo-panel grande">
            Reactor <span className="mono sub">{numero === null ? 'sin guardar' : `corrige N° ${String(numero).padStart(3, '0')}`}</span>
          </h2>
          <div className="segmentado" role="group" aria-label="Cámara">
            <button className={giro ? 'on' : ''} aria-pressed={giro} onClick={() => setGiro(!giro)}>
              Girar
            </button>
            <button onClick={() => setVistaKey((k) => k + 1)}>Vista 3D</button>
          </div>
        </div>

        {reacciones.length > 0 && (
          <div className="selector-reaccion">
            <label className="nota" htmlFor="reaccion">Reacción</label>
            <select id="reaccion" className="campo" value={reaccion?.id ?? ''} onChange={(e) => onReaccion(e.target.value)}>
              {reacciones.map((r) => (
                <option key={r.id} value={r.id}>{r.nombre}</option>
              ))}
            </select>
            {reaccion && <div className="mono nota ecuacion"><Formula texto={reaccion.ecuacion} /></div>}
          </div>
        )}

        <Escena3D estado={estado} giro={giro} vistaKey={vistaKey} />
        {componentes.length === 0 && <p className="pista">Soltá acá los compuestos de la biblioteca.</p>}

        <div className="composicion">
          <div className="composicion-cabecera">
            <span>Composición de la carga</span>
            <strong className="mono">{totalTexto} g</strong>
          </div>
          <div className="composicion-barra">
            {gramos
              .filter(({ g }) => g > 0)
              .map(({ x, g }) => (
                <span
                  key={x.uid}
                  style={{ flexGrow: g, background: colorDe(x.id) }}
                  title={`${porId.get(x.id)?.nombre ?? x.id}: ${Number(g.toPrecision(4))} g`}
                />
              ))}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-cabecera">
          <h2 className="titulo-panel grande">Carga</h2>
          <div className="acciones">
            <button className="btn btn-contorno" onClick={onEjemplo}>
              Cargar ejemplo
            </button>
            <button className="btn btn-contorno" onClick={onVaciar} disabled={componentes.length === 0}>
              Vaciar
            </button>
          </div>
        </div>
        {componentes.length === 0 ? (
          <p className="vacio">El reactor está vacío. Agregá compuestos desde la biblioteca.</p>
        ) : (
          componentes.map((x) => {
            const c = porId.get(x.id);
            return c ? (
              <ControlCompuesto
                key={x.uid}
                componente={x}
                compuesto={c}
                carga={resultado?.cargas.find((k) => k.id === x.id)}
                onCambiar={onCambiar}
                onQuitar={onQuitar}
              />
            ) : null;
          })
        )}
      </section>
    </div>
  );
}
