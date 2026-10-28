import { useCallback, useEffect, useState } from 'react';
import { compararEnsayos, guardarEnsayo, listarEnsayos, obtenerEnsayo } from '../../api/client';
import { useEnsayosLocales } from '../../hooks/useEnsayosLocales';
import {
  INCERTIDUMBRE_INICIAL,
  SIN_MEDIDOS,
  type ComparacionEnsayos as Comp,
  type Compuesto,
  type EnsayoResumen,
  type EnsayoServidor,
  type EstadoEnsayo,
  type Usuario,
} from '../../types';
import { ComparacionEnsayos } from './ComparacionEnsayos';
import { DetalleEnsayo } from './DetalleEnsayo';

interface Props {
  catalogo: Compuesto[];
  usuario: Usuario;
  /** Cambia cuando se guarda un ensayo desde el reactor, para refrescar la lista. */
  version: number;
  onCargar: (e: EnsayoServidor) => void;
  onCorregir: (e: EnsayoServidor) => void;
}

const POR_PAGINA = 20;
const colorDeValor = (v: number) => (v >= 75 ? 'var(--ok)' : v >= 50 ? 'var(--warn)' : 'var(--bad)');
const fmt = (n: number | null, dec = 1, suf = '') => (n === null ? '—' : `${n.toFixed(dec)}${suf}`);
const ETIQUETA_ORIGEN = { estimacion: 'Estimación', mixto: 'Mixto', medido: 'Medido' } as const;
const ETIQUETA_ESTADO: Record<EstadoEnsayo, string> = { registrado: 'Registrado', revisado: 'Revisado', aprobado: 'Aprobado', rechazado: 'Rechazado' };
const num = (id: number) => String(id).padStart(3, '0');

/** Ensayos guardados en el servidor: filtros, detalle con revisión, comparación y descarga de reportes. */
export function EnsayosVista({ catalogo, usuario, version, onCargar, onCorregir }: Props) {
  const [lista, setLista] = useState<EnsayoResumen[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lote, setLote] = useState('');
  const [loteAplicado, setLoteAplicado] = useState('');
  const [estado, setEstado] = useState<'' | EstadoEnsayo>('');
  const [soloVigentes, setSoloVigentes] = useState(false);
  const [pagina, setPagina] = useState(0);
  const [elegidos, setElegidos] = useState<number[]>([]);
  const [detalle, setDetalle] = useState<EnsayoServidor | null>(null);
  const [comparacion, setComparacion] = useState<Comp | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const { locales, quitar } = useEnsayosLocales();
  const [importando, setImportando] = useState(false);

  const refrescar = useCallback(() => {
    setCargando(true);
    listarEnsayos({ lote: loteAplicado, estado, soloVigentes, limit: POR_PAGINA, offset: pagina * POR_PAGINA })
      .then((r) => {
        setLista(r.ensayos);
        setTotal(r.total);
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Error desconocido'))
      .finally(() => setCargando(false));
  }, [loteAplicado, estado, soloVigentes, pagina]);

  useEffect(refrescar, [refrescar, version]);

  const abrir = (id: number) =>
    obtenerEnsayo(id)
      .then((e) => {
        setDetalle(e);
        setComparacion(null);
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Error desconocido'));

  const comparar = () =>
    compararEnsayos(elegidos)
      .then((c) => {
        setComparacion(c);
        setDetalle(null);
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Error desconocido'));

  const alternar = (id: number) =>
    setElegidos((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 8 ? [...prev, id] : prev));

  const importar = async () => {
    setImportando(true);
    const ok: number[] = [];
    const fallos: string[] = [];
    for (const l of [...locales].reverse()) {
      try {
        await guardarEnsayo(
          {
            componentes: l.componentes.map((c, i) => ({ ...c, uid: i })),
            reaccionId: l.reaccion_id ?? 'ibuprofeno-simplificada',
            medidos: l.medidos ?? SIN_MEDIDOS,
            incertidumbre: INCERTIDUMBRE_INICIAL,
          },
          {
            lote: '',
            corrigeA: null,
            notas: `Importado del navegador (ensayo local N° ${l.numero}, ${new Date(l.fecha).toLocaleString('es-AR')}). El servidor lo recalculó con el modelo vigente: el resultado puede diferir del que se veía entonces.`,
          },
        );
        ok.push(l.numero);
      } catch (e) {
        fallos.push(`N° ${l.numero}: ${e instanceof Error ? e.message.replace(/^Error \d+: /, '') : 'error'}`);
      }
    }
    quitar(ok);
    setImportando(false);
    setAviso(`Se importaron ${ok.length} de ${ok.length + fallos.length} ensayos.${fallos.length ? ' No se pudieron importar (siguen en este navegador): ' + fallos.join(' · ') : ''}`);
    refrescar();
  };

  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));
  const nombre = (id: string) => catalogo.find((c) => c.id === id)?.nombre ?? id;

  return (
    <div className="vista-ensayos">
      <section className="panel">
        <div className="panel-cabecera">
          <h2 className="titulo-panel grande">Ensayos guardados</h2>
          <span className="nota">{total} {total === 1 ? 'ensayo' : 'ensayos'} · guardados en el servidor, no se editan ni se borran</span>
        </div>

        {locales.length > 0 && (
          <div className="alerta warn" role="status">
            Hay {locales.length} {locales.length === 1 ? 'ensayo guardado' : 'ensayos guardados'} en este navegador (versión anterior).{' '}
            <button className="btn btn-contorno" onClick={importar} disabled={importando}>{importando ? 'Importando…' : 'Importarlos al servidor'}</button>
            <div className="nota">El servidor los recalcula con el modelo actual y deja constancia del origen en las notas.</div>
          </div>
        )}
        {aviso && <div className="alerta info" role="status">{aviso}</div>}

        <form className="filtros fila" onSubmit={(ev) => { ev.preventDefault(); setPagina(0); setLoteAplicado(lote); }}>
          <input className="campo" placeholder="Buscar por lote" aria-label="Buscar por lote" value={lote} onChange={(e) => setLote(e.target.value)} />
          <select className="campo" aria-label="Estado" value={estado} onChange={(e) => { setPagina(0); setEstado(e.target.value as '' | EstadoEnsayo); }}>
            <option value="">Todos los estados</option>
            {(Object.keys(ETIQUETA_ESTADO) as EstadoEnsayo[]).map((s) => <option key={s} value={s}>{ETIQUETA_ESTADO[s]}</option>)}
          </select>
          <label className="nota"><input type="checkbox" checked={soloVigentes} onChange={(e) => { setPagina(0); setSoloVigentes(e.target.checked); }} /> Solo vigentes</label>
          <button className="btn btn-contorno" type="submit">Buscar</button>
          <button type="button" className="btn btn-primario" disabled={elegidos.length < 2} onClick={comparar}>
            Comparar{elegidos.length ? ` (${elegidos.length})` : ''}
          </button>
        </form>

        {error && <div className="alerta bad" role="alert">{error}</div>}

        {!cargando && lista.length === 0 ? (
          <p className="vacio">No hay ensayos con estos filtros. Armá una mezcla en el Reactor y tocá «Guardar ensayo».</p>
        ) : (
          <div className="lista-ensayos">
            {lista.map((e) => (
              <article key={e.id} className={`ensayo con-check${e.vigente ? '' : ' reemplazado'}`}>
                <input type="checkbox" aria-label={`Elegir el ensayo ${num(e.id)} para comparar`} checked={elegidos.includes(e.id)} onChange={() => alternar(e.id)} />
                <div className="ensayo-num mono">N° {num(e.id)}</div>
                <div className="ensayo-cuerpo">
                  <div className="ensayo-fecha nota">
                    {new Date(e.creado_en).toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' })} · {e.usuario}
                    {e.lote && <> · lote <strong>{e.lote}</strong></>}
                  </div>
                  <div className="insignias">
                    <span className={`insignia estado-${e.estado}`}>{ETIQUETA_ESTADO[e.estado]}</span>
                    {e.origen && <span className={`insignia ${e.origen}`}>{ETIQUETA_ORIGEN[e.origen]}</span>}
                    {!e.vigente && <span className="insignia estimacion">Reemplazado por N° {num(e.reemplazado_por!)}</span>}
                    {e.corrige_a && <span className="insignia mixto">Corrige N° {num(e.corrige_a)}</span>}
                  </div>
                  <div className="nota">{e.reaccion_nombre || nombre(e.reaccion_id)}</div>
                </div>
                <div className="ensayo-metricas">
                  <div><span className="nota">Puntaje</span><strong className="mono" style={{ color: e.puntaje === null ? 'var(--tenue)' : colorDeValor(e.puntaje) }}>{e.puntaje ?? '—'}</strong></div>
                  <div><span className="nota">Rendimiento</span><strong className="mono">{fmt(e.rendimiento_pct, 1, '%')}</strong></div>
                  <div><span className="nota">Pureza</span><strong className="mono">{fmt(e.pureza_producto_pct, 1, '%')}</strong></div>
                </div>
                <div className="acciones">
                  <button className="btn btn-primario" onClick={() => abrir(e.id)}>Ver</button>
                </div>
              </article>
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

      {comparacion && <ComparacionEnsayos comparacion={comparacion} catalogo={catalogo} onCerrar={() => setComparacion(null)} />}
      {detalle && (
        <DetalleEnsayo
          ensayo={detalle}
          catalogo={catalogo}
          usuario={usuario}
          onActualizado={(e) => { setDetalle(e); refrescar(); }}
          onCargar={onCargar}
          onCorregir={onCorregir}
          onCerrar={() => setDetalle(null)}
        />
      )}
    </div>
  );
}
