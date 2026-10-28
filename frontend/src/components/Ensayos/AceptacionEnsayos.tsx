import { useCallback, useEffect, useRef, useState } from 'react';
import { agregarEvento, descargar, listarEnsayos, obtenerConteoEnsayos, obtenerEnsayo } from '../../api/client';
import {
  alcanzaRol,
  type Compuesto,
  type ConteoEstados,
  type EnsayoResumen,
  type EnsayoServidor,
  type EstadoEnsayo,
  type EstadoEspecificacion,
  type TipoEvento,
  type Usuario,
} from '../../types';
import './aceptacion.css';

interface Props {
  catalogo: Compuesto[];
  usuario: Usuario;
  /** Cambia cuando se guarda un ensayo desde el reactor, para refrescar la cola. */
  version: number;
  /** Se llama después de cada decisión, para que la cabecera actualice el globo de pendientes. */
  onCambio: () => void;
}

type Vista = 'revisar' | 'aprobar' | 'aprobados' | 'rechazados';

const VISTAS: Array<{ id: Vista; titulo: string; estado: EstadoEnsayo; pendiente: boolean; ayuda: string }> = [
  { id: 'revisar', titulo: 'Por revisar', estado: 'registrado', pendiente: true, ayuda: 'Cargados, sin revisión' },
  { id: 'aprobar', titulo: 'Por aprobar', estado: 'revisado', pendiente: true, ayuda: 'Revisados, falta aprobar' },
  { id: 'aprobados', titulo: 'Aprobados', estado: 'aprobado', pendiente: false, ayuda: 'Decisión final' },
  { id: 'rechazados', titulo: 'Rechazados', estado: 'rechazado', pendiente: false, ayuda: 'Decisión final' },
];

const POR_PAGINA = 15;
const ETIQUETA_ESTADO: Record<EstadoEnsayo, string> = { registrado: 'Registrado', revisado: 'Revisado', aprobado: 'Aprobado', rechazado: 'Rechazado' };
const ETIQUETA_EVENTO: Record<TipoEvento, string> = { comentario: 'Comentario', revisado: 'Revisado', aprobado: 'Aprobado', rechazado: 'Rechazado' };
const ETIQUETA_ORIGEN = { estimacion: 'Estimación', mixto: 'Mixto', medido: 'Medido' } as const;
const ETIQUETA_ESPEC: Record<EstadoEspecificacion, string> = { cumple: 'Cumple', no_cumple: 'No cumple', sin_dato: 'Sin dato', sin_limite: 'Sin límite' };
const ETIQUETA_BOTON: Record<TipoEvento, string> = { comentario: 'Comentar', revisado: 'Marcar revisado', aprobado: 'Aprobar', rechazado: 'Rechazar' };

const num = (id: number) => String(id).padStart(3, '0');
const colorDeValor = (v: number) => (v >= 75 ? 'var(--ok)' : v >= 50 ? 'var(--warn)' : 'var(--bad)');
const fmt = (n: number | null, dec = 1, suf = '') => (n === null ? '—' : `${n.toFixed(dec)}${suf}`);
const mensaje = (e: unknown) => (e instanceof Error ? e.message.replace(/^Error \d+: /, '') : 'Error desconocido');
const fecha = (iso: string) => new Date(iso).toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' });

function hace(iso: string): string {
  const min = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (min < 1) return 'recién';
  if (min < 60) return `hace ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.round(h / 24);
  return `hace ${d} ${d === 1 ? 'día' : 'días'}`;
}

function claseEspec(c: string | null): string {
  return c === 'cumple' ? 'cumple' : c === 'no_cumple' ? 'no_cumple' : 'sin_dato';
}
function etiquetaEspec(c: string | null): string {
  return c === 'cumple' ? 'Cumple' : c === 'no_cumple' ? 'No cumple' : c === 'incompleto' ? 'Incompleta' : 'Sin espec.';
}
function limites(min: number | null, max: number | null, unidad: string): string {
  if (min !== null && max !== null) return `${min} – ${max} ${unidad}`;
  if (min !== null) return `≥ ${min} ${unidad}`;
  if (max !== null) return `≤ ${max} ${unidad}`;
  return '—';
}

type Nivel = 'ok' | 'warn' | 'bad';
interface Control {
  nivel: Nivel;
  titulo: string;
  detalle?: string;
}

/** Lo que quien decide tiene que mirar antes de revisar o aprobar. Es una ayuda: el servidor no bloquea nada de esto salvo la autoría y el estado. */
function controlesDe(e: EnsayoServidor, usuario: Usuario): Control[] {
  const out: Control[] = [];
  const c = e.cumplimiento_especificaciones;
  if (c === 'cumple') out.push({ nivel: 'ok', titulo: 'Cumple la especificación', detalle: 'Todos los parámetros están dentro de los límites.' });
  else if (c === 'no_cumple') out.push({ nivel: 'bad', titulo: 'No cumple la especificación', detalle: 'Hay al menos un parámetro fuera de límite (ver la tabla).' });
  else if (c === 'incompleto') out.push({ nivel: 'warn', titulo: 'Especificación incompleta', detalle: 'Faltan mediciones o límites: no se puede afirmar que cumpla.' });
  else out.push({ nivel: 'warn', titulo: 'Sin especificación cargada' });

  if (e.origen === 'medido') out.push({ nivel: 'ok', titulo: 'Rendimiento y pureza medidos' });
  else if (e.origen === 'mixto') out.push({ nivel: 'warn', titulo: 'Datos mixtos', detalle: 'Una parte es medida y otra es estimación del modelo.' });
  else out.push({ nivel: 'warn', titulo: 'Solo estimación del modelo', detalle: 'No hay datos medidos en el laboratorio.' });

  if (e.vigente) out.push({ nivel: 'ok', titulo: 'Es la versión vigente' });
  else out.push({ nivel: 'bad', titulo: `Reemplazado por el N° ${num(e.reemplazado_por ?? 0)}`, detalle: 'Se decide sobre el ensayo que lo corrige.' });

  if (e.usuario_id === usuario.id) out.push({ nivel: 'bad', titulo: 'Lo hiciste vos', detalle: 'Lo decide otra persona de calidad.' });
  else out.push({ nivel: 'ok', titulo: `Hecho por ${e.usuario}`, detalle: 'Es otra persona: podés decidir.' });
  return out;
}

const ICONO: Record<Nivel, string> = { ok: '✓', warn: '!', bad: '✕' };

export function AceptacionEnsayos(props: Props) {
  if (!alcanzaRol(props.usuario.rol, 'calidad')) {
    return (
      <section className="panel">
        <p className="vacio">La aceptación de ensayos es del área de calidad. Con tu rol podés ver los ensayos en la pestaña «Ensayos».</p>
      </section>
    );
  }
  return <Panel {...props} />;
}

function Panel({ catalogo, usuario, version, onCambio }: Props) {
  const [vista, setVista] = useState<Vista>('revisar');
  const [pagina, setPagina] = useState(0);
  const [lista, setLista] = useState<EnsayoResumen[]>([]);
  const [total, setTotal] = useState(0);
  const [conteo, setConteo] = useState<ConteoEstados | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [seleccionId, setSeleccionId] = useState<number | null>(null);
  const [ensayo, setEnsayo] = useState<EnsayoServidor | null>(null);
  const [comentario, setComentario] = useState('');
  const [errorDecision, setErrorDecision] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  /** Lugar que ocupaba el ensayo elegido en la lista: al resolverlo, se pasa al que quedó en ese lugar (el siguiente de la cola). */
  const posicion = useRef(0);
  const pedido = useRef(0);

  const def = VISTAS.find((v) => v.id === vista) ?? VISTAS[0];
  const estadoVista = def.estado;
  const esPendiente = def.pendiente;

  const refrescar = useCallback(async () => {
    const mio = ++pedido.current;
    setCargando(true);
    try {
      const [r, c] = await Promise.all([
        listarEnsayos({ estado: estadoVista, soloVigentes: true, orden: esPendiente ? 'antiguos' : 'recientes', limit: POR_PAGINA, offset: pagina * POR_PAGINA }),
        obtenerConteoEnsayos(),
      ]);
      if (mio !== pedido.current) return; // llegó tarde: ya se pidió otra cosa
      setLista(r.ensayos);
      setTotal(r.total);
      setConteo(c);
      setError(null);
    } catch (e) {
      if (mio === pedido.current) setError(mensaje(e));
    } finally {
      if (mio === pedido.current) setCargando(false);
    }
  }, [estadoVista, esPendiente, pagina]);

  useEffect(() => {
    void refrescar();
  }, [refrescar, version]);

  // Si resolver el último de la página la deja vacía, se vuelve a la anterior.
  useEffect(() => {
    if (!cargando && lista.length === 0 && total > 0 && pagina > 0) setPagina((p) => p - 1);
  }, [cargando, lista, total, pagina]);

  // Siempre hay uno elegido mientras la lista tenga algo.
  useEffect(() => {
    if (lista.length === 0) {
      setSeleccionId(null);
      return;
    }
    setSeleccionId((actual) => {
      if (actual !== null && lista.some((e) => e.id === actual)) return actual;
      return lista[Math.min(posicion.current, lista.length - 1)].id;
    });
  }, [lista]);

  useEffect(() => {
    if (seleccionId === null) {
      setEnsayo(null);
      return;
    }
    let vigente = true;
    setComentario('');
    obtenerEnsayo(seleccionId)
      .then((e) => {
        if (!vigente) return;
        setEnsayo(e);
        setErrorDecision(null);
      })
      .catch((e: unknown) => {
        if (vigente) setErrorDecision(mensaje(e));
      });
    return () => {
      vigente = false;
    };
  }, [seleccionId, version]);

  const cambiarVista = (v: Vista) => {
    if (v === vista) return;
    setVista(v);
    setPagina(0);
    posicion.current = 0;
    setLista([]);
    setTotal(0);
    setSeleccionId(null);
    setEnsayo(null);
    setAviso(null);
    setCargando(true);
  };

  const elegir = (id: number) => {
    posicion.current = Math.max(0, lista.findIndex((e) => e.id === id));
    setSeleccionId(id);
    setAviso(null);
  };

  const decidir = async (tipo: TipoEvento) => {
    if (!ensayo) return;
    setOcupado(true);
    setErrorDecision(null);
    try {
      const nuevo = await agregarEvento(ensayo.id, tipo, comentario);
      const n = num(ensayo.id);
      setAviso(
        tipo === 'comentario' ? `Comentario agregado al N° ${n}.`
          : tipo === 'revisado' ? `N° ${n} revisado: pasó a «Por aprobar».`
          : tipo === 'aprobado' ? `N° ${n} aprobado.`
          : `N° ${n} rechazado.`,
      );
      setComentario('');
      if (tipo === 'comentario') {
        setEnsayo(nuevo);
      } else {
        posicion.current = Math.max(0, lista.findIndex((e) => e.id === ensayo.id));
      }
      await refrescar();
      onCambio();
    } catch (err) {
      setErrorDecision(mensaje(err));
    } finally {
      setOcupado(false);
    }
  };

  const nombre = (id: string) => catalogo.find((c) => c.id === id)?.nombre ?? id;
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));

  return (
    <div className="vista-aceptacion">
      <section className="panel">
        <div className="panel-cabecera">
          <h2 className="titulo-panel grande">Aceptación de ensayos</h2>
          <span className="nota">
            Se decide sobre el ensayo vigente. Cada revisión, aprobación o rechazo queda en la auditoría y no se puede deshacer.
          </span>
        </div>

        <div className="aceptacion-contadores" role="group" aria-label="Estado de los ensayos">
          {VISTAS.map((v) => {
            const n = conteo ? conteo[v.estado] : null;
            return (
              <button
                key={v.id}
                type="button"
                className={`contador vista-${v.estado}${vista === v.id ? ' activo' : ''}${v.pendiente ? ' pendiente' : ''}${n === 0 ? ' cero' : ''}`}
                aria-pressed={vista === v.id}
                onClick={() => cambiarVista(v.id)}
              >
                <span className="contador-num mono">{n ?? '—'}</span>
                <span className="contador-titulo">{v.titulo}</span>
                <span className="nota">{v.ayuda}</span>
              </button>
            );
          })}
        </div>
        {conteo !== null && conteo.reemplazados > 0 && (
          <p className="nota" style={{ margin: '10px 0 0' }}>
            {conteo.reemplazados} {conteo.reemplazados === 1 ? 'ensayo fue reemplazado' : 'ensayos fueron reemplazados'} por una corrección y ya no se {conteo.reemplazados === 1 ? 'revisa' : 'revisan'}.
          </p>
        )}
      </section>

      {aviso && <div className="alerta ok" role="status">{aviso}</div>}
      {error && <div className="alerta bad" role="alert">{error}</div>}

      <div className="aceptacion-cuerpo">
        <section className="panel" aria-label={def.titulo}>
          <div className="panel-cabecera">
            <h3 className="titulo-panel">{def.titulo} · {total}</h3>
            <span className="nota">{esPendiente ? 'Los que más esperan, primero' : 'Los más recientes, primero'}</span>
          </div>

          {cargando && lista.length === 0 ? (
            <p className="vacio">Cargando…</p>
          ) : lista.length === 0 ? (
            <p className="vacio">
              {esPendiente ? 'No hay ensayos esperando en esta etapa.' : `Todavía no hay ensayos ${def.estado === 'aprobado' ? 'aprobados' : 'rechazados'}.`}
            </p>
          ) : (
            <div className="cola">
              {lista.map((e) => (
                <button
                  key={e.id}
                  type="button"
                  className={`cola-item${e.id === seleccionId ? ' elegido' : ''}`}
                  aria-current={e.id === seleccionId ? 'true' : undefined}
                  aria-label={`Ensayo ${num(e.id)}${e.lote ? `, lote ${e.lote}` : ''}`}
                  onClick={() => elegir(e.id)}
                >
                  <span className="cola-num mono">N° {num(e.id)}</span>
                  <span className="cola-lote">{e.lote ?? 'sin lote'}</span>
                  <strong className="cola-puntaje mono" style={{ color: e.puntaje === null ? 'var(--tenue)' : colorDeValor(e.puntaje) }}>{e.puntaje ?? '—'}</strong>
                  <span className="cola-linea">
                    <span>{e.reaccion_nombre || nombre(e.reaccion_id)}</span>
                    <span>· {e.usuario}</span>
                    <span title={fecha(e.creado_en)}>· {hace(e.creado_en)}</span>
                    {!esPendiente && e.revision_por && e.revision_en && <span>· {e.revision_por}, {fecha(e.revision_en)}</span>}
                  </span>
                  <span className="cola-linea">
                    <span className={`estado ${claseEspec(e.cumplimiento_especificaciones)}`}>{etiquetaEspec(e.cumplimiento_especificaciones)}</span>
                    {e.origen && <span className={`insignia ${e.origen}`}>{ETIQUETA_ORIGEN[e.origen]}</span>}
                    {e.usuario_id === usuario.id && <span className="insignia estado-registrado">Tuyo</span>}
                    {e.n_comentarios > 0 && <span>{e.n_comentarios} {e.n_comentarios === 1 ? 'comentario' : 'comentarios'}</span>}
                  </span>
                </button>
              ))}
            </div>
          )}

          {paginas > 1 && (
            <div className="paginacion">
              <button className="btn btn-contorno" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>← Anteriores</button>
              <span className="nota">Página {pagina + 1} de {paginas}</span>
              <button className="btn btn-contorno" disabled={pagina + 1 >= paginas} onClick={() => setPagina((p) => p + 1)}>Siguientes →</button>
            </div>
          )}
        </section>

        {ensayo ? (
          <Decision
            ensayo={ensayo}
            usuario={usuario}
            catalogo={catalogo}
            comentario={comentario}
            onComentario={setComentario}
            ocupado={ocupado}
            error={errorDecision}
            onDecidir={decidir}
            onError={setErrorDecision}
          />
        ) : (
          <section className="panel decision">
            <p className="vacio">{lista.length === 0 && !cargando ? 'No hay un ensayo para mostrar.' : 'Elegí un ensayo de la lista.'}</p>
            {errorDecision && <div className="alerta bad" role="alert">{errorDecision}</div>}
          </section>
        )}
      </div>
    </div>
  );
}

interface PropsDecision {
  ensayo: EnsayoServidor;
  usuario: Usuario;
  catalogo: Compuesto[];
  comentario: string;
  onComentario: (t: string) => void;
  ocupado: boolean;
  error: string | null;
  onDecidir: (t: TipoEvento) => void;
  onError: (m: string) => void;
}

function Decision({ ensayo: e, usuario, catalogo, comentario, onComentario, ocupado, error, onDecidir, onError }: PropsDecision) {
  const r = e.salida.resultado;
  const nombre = (id: string) => catalogo.find((c) => c.id === id)?.nombre ?? id;
  const esAutor = e.usuario_id === usuario.id;
  const puedeDecidir = !esAutor && e.vigente && (e.estado === 'registrado' || e.estado === 'revisado');
  const acciones: TipoEvento[] = e.estado === 'registrado' ? ['revisado', 'rechazado'] : e.estado === 'revisado' ? ['aprobado', 'rechazado'] : [];
  const sinCumplir = e.cumplimiento_especificaciones !== 'cumple';
  const exigeTexto = (t: TipoEvento) => t === 'rechazado' || (t === 'aprobado' && sinCumplir);
  const hayTexto = comentario.trim().length > 0;
  const controles = controlesDe(e, usuario);

  return (
    <section className="panel sobre decision" aria-label={`Ensayo ${num(e.id)}`}>
      <div className="panel-cabecera">
        <h3 className="titulo-panel grande">Ensayo N° {num(e.id)}{e.lote ? ` · lote ${e.lote}` : ''}</h3>
        <div className="acciones">
          <button
            className="btn btn-contorno"
            onClick={() => descargar(`/ensayos/${e.id}/reporte.pdf`, `ensayo-${num(e.id)}.pdf`).catch((err: unknown) => onError(mensaje(err)))}
          >
            PDF
          </button>
        </div>
      </div>

      <div className="insignias">
        <span className={`insignia estado-${e.estado}`}>{ETIQUETA_ESTADO[e.estado]}</span>
        {e.origen && <span className={`insignia ${e.origen}`}>{ETIQUETA_ORIGEN[e.origen]}</span>}
        {e.corrige_a && <span className="insignia mixto">Corrige al N° {num(e.corrige_a)}</span>}
      </div>
      <p className="nota" style={{ margin: '0 0 8px' }}>
        {e.reaccion_nombre || nombre(e.reaccion_id)} · hecho por {e.usuario} el {fecha(e.creado_en)} · modelo <span className="mono">{e.version_modelo}</span>
      </p>

      <div className="decision-metricas">
        <div><span className="nota">Puntaje</span><strong className="mono" style={{ color: e.puntaje === null ? 'var(--tenue)' : colorDeValor(e.puntaje) }}>{e.puntaje ?? '—'}</strong></div>
        <div><span className="nota">Rendimiento</span><strong className="mono">{fmt(e.rendimiento_pct, 1, ' %')}</strong></div>
        <div><span className="nota">Pureza</span><strong className="mono">{fmt(e.pureza_producto_pct, 1, ' %')}</strong></div>
        <div><span className="nota">Producto</span><strong className="mono">{fmt(e.gramos_estimados, 1, ' g')}</strong></div>
      </div>

      <h4 className="subtitulo">Antes de decidir</h4>
      <ul className="controles">
        {controles.map((c) => (
          <li key={c.titulo} className={`control ${c.nivel}`}>
            <span className="control-icono" aria-hidden>{ICONO[c.nivel]}</span>
            <span>
              {c.titulo}
              {c.detalle && <small>{c.detalle}</small>}
            </span>
          </li>
        ))}
      </ul>

      {r && r.especificaciones.length > 0 && (
        <>
          <h4 className="subtitulo">Especificación</h4>
          <div className="tabla-ancha">
            <table className="tabla-spec">
              <thead>
                <tr><th>Parámetro</th><th>Límite</th><th className="num">Valor</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {r.especificaciones.map((s) => (
                  <tr key={s.id}>
                    <td>{s.parametro}</td>
                    <td className="mono">{limites(s.minimo, s.maximo, s.unidad)}</td>
                    <td className="num mono">
                      {s.valor === null ? '—' : `${+s.valor.toFixed(3)} ${s.unidad}`}
                      {s.origen && <span className={`origen-tag ${s.origen}`}>{s.origen === 'medido' ? 'medido' : 'modelo'}</span>}
                    </td>
                    <td><span className={`estado ${s.estado}`}>{ETIQUETA_ESPEC[s.estado]}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <h4 className="subtitulo">Carga</h4>
      <div className="ensayo-composicion">
        {e.entrada.componentes.map((x) => (
          <span key={x.id} className="chip">
            {nombre(x.id)} <span className="mono">{x.gramos !== null ? `${x.gramos} g` : `${x.cantidad} ${x.unidad}`}</span>
            <span className="mono">· pureza {x.pureza} %</span>
          </span>
        ))}
      </div>
      {e.notas && (<><h4 className="subtitulo">Notas</h4><p className="notas-ensayo">{e.notas}</p></>)}

      <h4 className="subtitulo">Revisión y comentarios</h4>
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

      <div className="decision-acciones">
        <textarea
          className="campo"
          rows={2}
          maxLength={4000}
          placeholder="Comentario (obligatorio para rechazar y para aprobar algo que no cumple)"
          aria-label="Comentario"
          value={comentario}
          onChange={(ev) => onComentario(ev.target.value)}
        />
        {puedeDecidir && e.estado === 'revisado' && sinCumplir && (
          <div className="alerta warn" role="note">
            La especificación no está cumplida de punta a punta: para aprobar, dejá escrita la justificación.
          </div>
        )}
        <div className="acciones">
          <button className="btn btn-contorno" disabled={ocupado || !hayTexto} onClick={() => onDecidir('comentario')}>{ETIQUETA_BOTON.comentario}</button>
          {puedeDecidir && acciones.map((t) => (
            <button
              key={t}
              className={`btn ${t === 'rechazado' ? 'btn-contorno btn-peligro' : 'btn-primario'}`}
              disabled={ocupado || (exigeTexto(t) && !hayTexto)}
              onClick={() => onDecidir(t)}
            >
              {ETIQUETA_BOTON[t]}
            </button>
          ))}
        </div>
        {!puedeDecidir && (e.estado === 'registrado' || e.estado === 'revisado') && (
          <p className="nota">
            {esAutor ? 'Hiciste este ensayo: lo revisa y lo aprueba otra persona de calidad.' : !e.vigente ? `Fue reemplazado por el N° ${num(e.reemplazado_por ?? 0)}: se decide sobre ese.` : ''}
          </p>
        )}
        {(e.estado === 'aprobado' || e.estado === 'rechazado') && (
          <p className="nota decision-resuelta">
            {e.estado === 'aprobado' ? 'Aprobado' : 'Rechazado'} por {e.revision_por ?? '—'}{e.revision_en ? ` el ${fecha(e.revision_en)}` : ''}. La decisión es definitiva: si hay que cambiar algo, se corrige con un ensayo nuevo.
          </p>
        )}
      </div>
      {error && <div className="alerta bad" role="alert">{error}</div>}
    </section>
  );
}
