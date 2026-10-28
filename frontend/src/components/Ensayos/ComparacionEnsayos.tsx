import { descargar } from '../../api/client';
import type { ComparacionEnsayos as Comp, Compuesto } from '../../types';

interface Props {
  comparacion: Comp;
  catalogo: Compuesto[];
  onCerrar: () => void;
}

const num = (id: number) => String(id).padStart(3, '0');
const celda = (v: string | number | null | undefined) => (v === null || v === undefined ? '—' : typeof v === 'number' ? String(v) : v);

/** Ensayos lado a lado: métricas y carga de cada compuesto. */
export function ComparacionEnsayos({ comparacion: c, catalogo, onCerrar }: Props) {
  const ids = c.ensayos.map((e) => e.id);
  const nombre = (id: string) => catalogo.find((x) => x.id === id)?.nombre ?? id;
  return (
    <section className="panel sobre" aria-label="Comparación de ensayos">
      <div className="panel-cabecera">
        <h2 className="titulo-panel grande">Comparación</h2>
        <div className="acciones">
          <button className="btn btn-contorno" onClick={() => descargar(`/ensayos/comparar.xlsx?ids=${ids.join(',')}`, 'comparacion-ensayos.xlsx')}>Excel</button>
          <button className="btn btn-contorno" onClick={onCerrar} aria-label="Cerrar comparación">✕</button>
        </div>
      </div>
      <div className="tabla-ancha">
        <table className="tabla multi">
          <thead>
            <tr><th>Métrica</th>{ids.map((i) => <th key={i}>N° {num(i)}</th>)}</tr>
          </thead>
          <tbody>
            <tr><td>Lote</td>{c.ensayos.map((e) => <td key={e.id}>{e.lote ?? '—'}</td>)}</tr>
            <tr><td>Estado</td>{c.ensayos.map((e) => <td key={e.id}>{e.estado}{e.vigente ? '' : ' (reemplazado)'}</td>)}</tr>
            {c.metricas.map((m) => (
              <tr key={m.metrica}><td>{m.metrica}</td>{ids.map((i) => <td key={i}>{celda(m.valores[String(i)])}</td>)}</tr>
            ))}
            <tr><th colSpan={ids.length + 1}>Carga (g de material)</th></tr>
            {c.compuestos.map((x) => (
              <tr key={x.id}><td>{nombre(x.id)}</td>{ids.map((i) => <td key={i}>{celda(x.gramos[String(i)])}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      {new Set(c.ensayos.map((e) => e.version_modelo)).size > 1 && (
        <div className="alerta warn">Estos ensayos se calcularon con distintas versiones del modelo: las diferencias pueden venir del modelo y no de la mezcla.</div>
      )}
    </section>
  );
}
