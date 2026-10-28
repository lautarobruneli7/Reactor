import { useState } from 'react';
import type { Compuesto } from '../../types';
import { colorDe } from './colores';
import { CATEGORIAS, categoriaDe, filtrar, Formula } from './categorias';

interface Props {
  compuestos: Compuesto[];
  usados: string[];
  onAgregar: (id: string) => void;
  onAbrirBiblioteca: () => void;
}

/** Panel lateral compacto: buscar, filtrar y arrastrar compuestos al reactor (o tocarlos para agregarlos). */
export function Catalogo({ compuestos, usados, onAgregar, onAbrirBiblioteca }: Props) {
  const [busqueda, setBusqueda] = useState('');
  const [categoria, setCategoria] = useState('todas');
  const visibles = filtrar(compuestos, busqueda, categoria);

  return (
    <section className="panel lateral">
      <h2 className="titulo-panel grande">Biblioteca</h2>
      <div className="filtros">
        <input
          className="campo"
          type="search"
          placeholder="Buscar nombre o fórmula"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
        />
        <select className="campo" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          <option value="todas">Todas las categorías</option>
          {CATEGORIAS.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="lista-compuestos">
        {CATEGORIAS.map((cat) => {
          const grupo = visibles.filter((c) => categoriaDe(c) === cat);
          if (grupo.length === 0) return null;
          return (
            <div key={cat}>
              <div className="grupo-titulo">{cat}</div>
              {grupo.map((c) => (
                <div
                  key={c.id}
                  className={`fila-compuesto${usados.includes(c.id) ? ' usado' : ''}`}
                  style={{ ['--c' as string]: colorDe(c.id) }}
                  draggable
                  role="button"
                  tabIndex={0}
                  title="Arrastralo al reactor o tocalo para agregarlo"
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/plain', c.id);
                    e.dataTransfer.effectAllowed = 'copy';
                  }}
                  onClick={() => onAgregar(c.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onAgregar(c.id);
                    }
                  }}
                >
                  <span className="punto-color" />
                  <span className="fila-nombre">{c.nombre}</span>
                  <span className="formula mono">
                    <Formula texto={c.formula} />
                  </span>
                </div>
              ))}
            </div>
          );
        })}
        {visibles.length === 0 && <p className="vacio">Sin resultados.</p>}
      </div>

      <button className="btn btn-contorno ancho" onClick={onAbrirBiblioteca}>
        Abrir biblioteca completa
      </button>
    </section>
  );
}
