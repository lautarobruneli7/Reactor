import { useState } from 'react';
import { agregarEvento, descargar } from '../../api/client';
import { alcanzaRol, type Compuesto, type EnsayoServidor, type TipoEvento, type Usuario } from '../../types';

interface Props {
  ensayo: EnsayoServidor;
  catalogo: Compuesto[];
  usuario: Usuario;
  onActualizado: (e: EnsayoServidor) => void;
  onCargar: (e: EnsayoServidor) => void;
  onCorregir: (e: EnsayoServidor) => void;
  onCerrar: () => void;
}

const ETIQUETA_ESTADO = { registrado: 'Registrado', revisado: 'Revisado', aprobado: 'Aprobado', rechazado: 'Rechazado' } as const;
const ETIQUETA_EVENTO: Record<TipoEvento, string> = { comentario: 'Comentario', revisado: 'Revisado', aprobado: 'Aprobado', rechazado: 'Rechazado' };
const ESPEC = {
  cumple: 'Cumple la especificación en todos los parámetros',
  no_cumple: 'NO cumple la especificación',
  incompleto: 'Especificación incompleta: faltan mediciones o límites, no se puede afirmar que cumpla',
  sin_especificaciones: 'Sin especificación cargada',
} as const;
const fecha = (iso: string) => new Date(iso).toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' });
const num = (id: number) => String(id).padStart(3, '0');

export function DetalleEnsayo({ ensayo: e, catalogo, usuario, onActualizado, onCargar, onCorregir, onCerrar }: Props) {
  const [comentario, setComentario] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const nombre = (id: string) => catalogo.find((c) => c.id === id)?.nombre ?? id;
  const r = e.salida.resultado;

  const esCalidad = alcanzaRol(usuario.rol, 'calidad');
  const esAutor = e.usuario_id === usuario.id;
  const puedeRevisar = esCalidad && !esAutor && e.vigente;
  const acciones: TipoEvento[] = e.estado === 'registrado' ? ['revisado', 'rechazado'] : e.estado === 'revisado' ? ['aprobado', 'rechazado'] : [];
  const puedeCorregir = alcanzaRol(usuario.rol, 'analista') && e.vigente && (esAutor || esCalidad);

  const evento = async (tipo: TipoEvento) => {
    setOcupado(true);
    setError(null);
    try {
      onActualizado(await agregarEvento(e.id, tipo, comentario));
      setComentario('');
    } catch (err) {
      setError(err instanceof Error ? err.message.replace(/^Error \d+: /, '') : 'No se pudo registrar');
    } finally {
      setOcupado(false);
    }
  };

  const bajar = (ruta: string, nombreArchivo: string) =>
    descargar(ruta, nombreArchivo).catch((err: unknown) => setError(err instanceof Error ? err.message : 'No se pudo descargar'));

  return (
    <section className="panel sobre detalle-ensayo" aria-label={`Detalle del ensayo ${num(e.id)}`}>
      <div className="panel-cabecera">
        <h2 className="titulo-panel grande">Ensayo N° {num(e.id)}</h2>
        <div className="acciones">
          <button className="btn btn-contorno" onClick={() => bajar(`/ensayos/${e.id}/reporte.pdf`, `ensayo-${num(e.id)}.pdf`)}>PDF</button>
          <button className="btn btn-contorno" onClick={() => bajar(`/ensayos/${e.id}/reporte.xlsx`, `ensayo-${num(e.id)}.xlsx`)}>Excel</button>
          <button className="btn btn-contorno" onClick={() => onCargar(e)}>Cargar en el reactor</button>
          {puedeCorregir && <button className="btn btn-primario" onClick={() => onCorregir(e)}>Corregir…</button>}
          <button className="btn btn-contorno" onClick={onCerrar} aria-label="Cerrar detalle">✕</button>
        </div>
      </div>

      <div className="insignias">
        <span className={`insignia estado-${e.estado}`}>{ETIQUETA_ESTADO[e.estado]}</span>
        {!e.vigente && <span className="insignia estimacion">Reemplazado por N° {num(e.reemplazado_por!)}</span>}
        {e.corrige_a && <span className="insignia mixto">Corrige al N° {num(e.corrige_a)}</span>}
        {e.origen && <span className={`insignia ${e.origen}`}>{e.origen === 'medido' ? 'Medido' : e.origen === 'mixto' ? 'Mixto' : 'Estimación'}</span>}
      </div>

      <table className="tabla">
        <tbody>
          <tr><td>Reacción</td><td>{e.reaccion_nombre}</td></tr>
          <tr><td>Lote</td><td>{e.lote ?? '—'}</td></tr>
          <tr><td>Realizado por</td><td>{e.usuario} · {fecha(e.creado_en)}</td></tr>
          <tr><td>Versión del modelo</td><td className="mono">{e.version_modelo}</td></tr>
          {r && <tr><td>Puntaje / rendimiento / pureza</td><td className="mono">{r.puntaje} · {r.rendimiento_pct.toFixed(1)} % · {r.pureza_producto_pct.toFixed(1)} %</td></tr>}
          {r && <tr><td>Especificación</td><td>{ESPEC[r.cumplimiento_especificaciones]}</td></tr>}
          <tr><td>Huella del ensayo</td><td className="corto mono">{e.digest}</td></tr>
          {e.sello && <tr><td>Registro N° {e.sello.id}</td><td className="corto mono">{e.sello.hash}</td></tr>}
        </tbody>
      </table>

      <h3 className="subtitulo">Carga</h3>
      <div className="ensayo-composicion">
        {e.entrada.componentes.map((x) => (
          <span key={x.id} className="chip">
            {nombre(x.id)} <span className="mono">{x.gramos !== null ? `${x.gramos} g` : `${x.cantidad} ${x.unidad}`}</span>
            <span className="mono">· pureza {x.pureza} %</span>
            {x.concentracion && <span className="mono">· {x.concentracion.valor} {x.concentracion.tipo === 'molar' ? 'mol/L' : x.concentracion.tipo === 'p/p' ? '% p/p' : '% p/v'}</span>}
          </span>
        ))}
      </div>
      {e.notas && (<><h3 className="subtitulo">Notas</h3><p className="notas-ensayo">{e.notas}</p></>)}

      <h3 className="subtitulo">Revisión y comentarios</h3>
      {e.eventos.length === 0 ? <p className="nota">Todavía no hay revisión ni comentarios.</p> : (
        <ul className="eventos">
          {e.eventos.map((v) => (
            <li key={v.id}>
              <span className={`insignia estado-${v.tipo}`}>{ETIQUETA_EVENTO[v.tipo]}</span>{' '}
              <strong>{v.usuario}</strong> <span className="nota">{fecha(v.creado_en)}</span>
              {v.comentario && <div>{v.comentario}</div>}
            </li>
          ))}
        </ul>
      )}

      {alcanzaRol(usuario.rol, 'analista') && (
        <div className="evento-nuevo">
          <textarea className="campo" rows={2} placeholder="Comentario (obligatorio para rechazar)" aria-label="Comentario" value={comentario} onChange={(ev) => setComentario(ev.target.value)} maxLength={4000} />
          <div className="acciones">
            <button className="btn btn-contorno" disabled={ocupado || !comentario.trim()} onClick={() => evento('comentario')}>Comentar</button>
            {puedeRevisar && acciones.map((t) => (
              <button key={t} className={`btn ${t === 'rechazado' ? 'btn-contorno btn-peligro' : 'btn-primario'}`} disabled={ocupado || (t === 'rechazado' && !comentario.trim())} onClick={() => evento(t)}>
                {t === 'revisado' ? 'Marcar revisado' : t === 'aprobado' ? 'Aprobar' : 'Rechazar'}
              </button>
            ))}
          </div>
          {esCalidad && esAutor && e.estado !== 'aprobado' && <p className="nota">Quien hizo el ensayo no puede revisarlo ni aprobarlo: tiene que hacerlo otra persona de calidad.</p>}
          {!esCalidad && <p className="nota">Revisar, aprobar o rechazar requiere el rol de calidad.</p>}
        </div>
      )}
      {error && <div className="alerta bad" role="alert">{error}</div>}
    </section>
  );
}
