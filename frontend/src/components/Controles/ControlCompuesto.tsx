import type { CargaResuelta, ComponenteEnReactor, Compuesto, TipoConcentracion, UnidadCantidad } from '../../types';
import { UNIDADES } from '../../types';
import { textoCantidad } from '../../utilidades/cargas';
import { colorDe } from '../Compuestos/colores';
import { CampoNumero } from './CampoNumero';

export type CambiosComponente = Partial<Omit<ComponenteEnReactor, 'uid' | 'id'>>;

interface Props {
  componente: ComponenteEnReactor;
  compuesto: Compuesto;
  /** Cómo quedó esta carga después de convertir unidades y concentración (viene del resultado). */
  carga?: CargaResuelta;
  onCambiar: (uid: number, cambios: CambiosComponente) => void;
  onQuitar: (uid: number) => void;
}

const TIPOS: Array<[TipoConcentracion, string]> = [
  ['p/p', '% p/p (masa)'],
  ['p/v', '% p/v (g/100 mL)'],
  ['molar', 'mol/L (molar)'],
];

/**
 * Fila de la carga: cantidad, unidad, pureza y, si viene en solución, su concentración.
 * Pureza y concentración son datos distintos: HCl 37 % p/p no es HCl con 37 % de pureza.
 */
export function ControlCompuesto({ componente, compuesto, carga, onCambiar, onQuitar }: Props) {
  const enGramos = componente.unidad === 'g';
  const esSolucion = componente.concentracion !== null;
  const porVolumen = componente.unidad === 'mL' || componente.unidad === 'L';
  const pideDensidad = porVolumen || (esSolucion && componente.concentracion!.tipo !== 'p/p');
  const nombre = compuesto.nombre;

  return (
    <div className="item-carga" style={{ ['--c' as string]: colorDe(compuesto.id) }}>
      <div className="item-linea">
        <span className="punto-color" />
        <strong className="item-nombre">{nombre}</strong>
        {enGramos ? (
          <input
            type="range"
            aria-label={`Cantidad de ${nombre}`}
            min={0}
            max={400}
            step={1}
            style={{ ['--p' as string]: `${(Math.min(componente.cantidad, 400) / 400) * 100}%` }}
            value={Math.min(componente.cantidad, 400)}
            onChange={(e) => onCambiar(componente.uid, { cantidad: Number(e.target.value) })}
          />
        ) : (
          <span className="cantidad-num">
            <CampoNumero
              className="campo mono"
              ariaLabel={`Cantidad de ${nombre}`}
              min={0}
              value={componente.cantidad}
              onValor={(v) => v !== null && onCambiar(componente.uid, { cantidad: Math.max(0, v) })}
            />
          </span>
        )}
        <output className="mono valor-g">{enGramos ? `${componente.cantidad} g` : componente.unidad}</output>
        <button className="btn-quitar" title="Quitar del reactor" aria-label={`Quitar ${nombre}`} onClick={() => onQuitar(componente.uid)}>
          ✕
        </button>
      </div>

      <div className="item-extra">
        <label>
          Unidad
          <select
            className="campo"
            aria-label={`Unidad de ${nombre}`}
            value={componente.unidad}
            onChange={(e) => onCambiar(componente.uid, { unidad: e.target.value as UnidadCantidad })}
          >
            {UNIDADES.map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
        </label>
        <label>
          Pureza
          <CampoNumero
            ariaLabel={`Pureza de ${nombre}`}
            min={0}
            max={100}
            step={0.5}
            value={componente.pureza}
            onValor={(v) => v !== null && onCambiar(componente.uid, { pureza: Math.min(100, Math.max(0, v)) })}
          />
          %
        </label>
        <label className="casilla">
          <input
            type="checkbox"
            aria-label={`${nombre} viene en solución`}
            checked={esSolucion}
            onChange={(e) => onCambiar(componente.uid, { concentracion: e.target.checked ? { tipo: 'p/p', valor: 37 } : null })}
          />
          En solución
        </label>
        {esSolucion && componente.concentracion && (
          <>
            <label>
              Concentración
              <CampoNumero
                ariaLabel={`Concentración de ${nombre}`}
                min={0}
                step="any"
                value={componente.concentracion.valor}
                onValor={(v) =>
                  v !== null && v > 0 && onCambiar(componente.uid, { concentracion: { ...componente.concentracion!, valor: v } })
                }
              />
            </label>
            <select
              className="campo"
              aria-label={`Tipo de concentración de ${nombre}`}
              value={componente.concentracion.tipo}
              onChange={(e) =>
                onCambiar(componente.uid, { concentracion: { ...componente.concentracion!, tipo: e.target.value as TipoConcentracion } })
              }
            >
              {TIPOS.map(([t, n]) => (
                <option key={t} value={t}>
                  {n}
                </option>
              ))}
            </select>
          </>
        )}
        {pideDensidad && (
          <label>
            Densidad
            <CampoNumero
              ariaLabel={`Densidad de ${nombre}`}
              min={0}
              step="any"
              placeholder={esSolucion ? 'g/mL' : 'catálogo'}
              value={componente.densidad}
              onValor={(v) => onCambiar(componente.uid, { densidad: v !== null && v > 0 ? v : null })}
            />
            g/mL
          </label>
        )}
      </div>

      {carga && (!enGramos || esSolucion) && (
        <div className="item-resuelto mono">
          = {textoCantidad(carga.gramos_material, 'g')} de material
          {carga.fraccion_soluto < 1 && ` · ${(carga.fraccion_soluto * 100).toFixed(1)} % es ${nombre.toLowerCase()}`}
          {carga.moles_netos !== null && ` · ${textoCantidad(carga.moles_netos, 'mol')} netos`}
        </div>
      )}
    </div>
  );
}
