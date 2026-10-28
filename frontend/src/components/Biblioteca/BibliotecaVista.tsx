import { useEffect, useState } from 'react';
import { obtenerPropiedades } from '../../api/client';
import type { Compuesto } from '../../types';
import { colorDe } from '../Compuestos/colores';
import { CATEGORIAS, categoriaDe, filtrar, Formula } from '../Compuestos/categorias';

interface Props {
  compuestos: Compuesto[];
  usados: string[];
  onAgregar: (id: string) => void;
  onIrReactor: () => void;
}

type Props3D = Record<string, number | string>;

/** Detalle de un compuesto; las propiedades moleculares se piden al backend (necesitan RDKit). */
function Detalle({ c, usado, onAgregar, onIrReactor }: { c: Compuesto; usado: boolean; onAgregar: () => void; onIrReactor: () => void }) {
  const [props, setProps] = useState<Props3D | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    setProps(null);
    setAviso(null);
    if (!c.smiles) {
      setAviso('Este compuesto no tiene estructura molecular cargada.');
      return;
    }
    let vigente = true;
    obtenerPropiedades(c.id)
      .then((p) => vigente && setProps(p))
      .catch((e: unknown) => vigente && setAviso(e instanceof Error ? e.message.replace(/^Error \d+: /, '') : 'No disponible.'));
    return () => {
      vigente = false;
    };
  }, [c]);

  return (
    <aside className="panel detalle" style={{ ['--c' as string]: colorDe(c.id) }}>
      <div className="detalle-cabecera">
        <span className="punto-color grande" />
        <div>
          <h2 className="titulo-panel grande">{c.nombre}</h2>
          <div className="nota">{categoriaDe(c)} · {c.rol}</div>
        </div>
      </div>
      <table className="tabla">
        <tbody>
          <tr><td>Fórmula</td><td className="mono"><Formula texto={c.formula} /></td></tr>
          {c.cas && <tr><td>N° CAS</td><td className="mono">{c.cas}</td></tr>}
          <tr><td>Peso molecular</td><td className="mono">{c.pm > 0 ? `${c.pm} g/mol` : '—'}</td></tr>
          {c.tm_c !== null && <tr><td>Punto de fusión</td><td className="mono">{c.tm_c} °C</td></tr>}
          {c.tb_c !== null && <tr><td>Punto de ebullición</td><td className="mono">{c.tb_c} °C</td></tr>}
          <tr><td>Fase</td><td>{c.fase}</td></tr>
          <tr><td>Tipo</td><td>{c.tipo}</td></tr>
          {c.smiles && <tr><td>SMILES</td><td className="mono corto">{c.smiles}</td></tr>}
          <tr><td>Fuente del dato</td><td>{c.fuente}</td></tr>
        </tbody>
      </table>

      {c.acceso === 'controlado' && c.regulacion && <div className="alerta warn">{c.regulacion}</div>}
      {c.nota && <p className="nota">{c.nota}</p>}
      {!c.verificado && c.pm_aplicable && <p className="nota">Fórmula y peso molecular sin contrastar con la base pública.</p>}

      <h3 className="subtitulo">Propiedades moleculares</h3>
      {props && (
        <table className="tabla">
          <tbody>
            {Object.entries(props).map(([k, v]) => (
              <tr key={k}><td>{k}</td><td className="mono">{String(v)}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {aviso && <p className="nota">{aviso}</p>}
      {!props && !aviso && <p className="nota">Cargando…</p>}

      <div className="acciones">
        <button className="btn btn-primario" onClick={usado ? onIrReactor : onAgregar}>
          {usado ? 'Ya está en el reactor · Ir' : 'Agregar al reactor'}
        </button>
      </div>
    </aside>
  );
}

export function BibliotecaVista({ compuestos, usados, onAgregar, onIrReactor }: Props) {
  const [busqueda, setBusqueda] = useState('');
  const [categoria, setCategoria] = useState('todas');
  const [elegido, setElegido] = useState<string | null>(null);
  const visibles = filtrar(compuestos, busqueda, categoria);
  const detalle = compuestos.find((c) => c.id === elegido) ?? null;

  return (
    <div className="vista-doble">
      <section className="panel">
        <div className="panel-cabecera">
          <h2 className="titulo-panel grande">Biblioteca de compuestos</h2>
          <span className="nota">{visibles.length} de {compuestos.length}</span>
        </div>
        <div className="filtros fila">
          <input className="campo" type="search" placeholder="Buscar nombre o fórmula" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
          <select className="campo" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            <option value="todas">Todas las categorías</option>
            {CATEGORIAS.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>

        <div className="rejilla">
          {visibles.map((c) => (
            <button
              key={c.id}
              className={`tarjeta${elegido === c.id ? ' elegida' : ''}`}
              style={{ ['--c' as string]: colorDe(c.id) }}
              onClick={() => setElegido(c.id)}
            >
              <span className="punto-color" />
              <strong>{c.nombre}</strong>
              <span className="formula mono"><Formula texto={c.formula} /></span>
              <span className="nota">{categoriaDe(c)} · {c.fase}{c.pm > 0 ? ` · PM ${c.pm}` : ''}</span>
              {usados.includes(c.id) && <span className="etiqueta">En el reactor</span>}
              {c.acceso === 'controlado' && !usados.includes(c.id) && <span className="etiqueta controlado">Controlado</span>}
            </button>
          ))}
          {visibles.length === 0 && <p className="vacio">Sin resultados.</p>}
        </div>
      </section>

      {detalle ? (
        <Detalle c={detalle} usado={usados.includes(detalle.id)} onAgregar={() => onAgregar(detalle.id)} onIrReactor={onIrReactor} />
      ) : (
        <aside className="panel detalle"><p className="vacio">Elegí un compuesto para ver su detalle.</p></aside>
      )}
    </div>
  );
}
