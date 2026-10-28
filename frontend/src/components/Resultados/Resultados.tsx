import { useState } from 'react';
import type {
  Alerta,
  CumplimientoGlobal,
  EvaluacionEspecificacion,
  Especificacion,
  IntervaloMetrica,
  Medidos,
  OpcionesIncertidumbre,
  Resultado,
} from '../../types';
import { Formula } from '../Compuestos/categorias';
import { CampoNumero } from '../Controles/CampoNumero';

interface Props {
  resultado: Resultado | null;
  alertas: Alerta[];
  cargando: boolean;
  error: string | null;
  /** Pureza mínima exigida, para marcarla sobre la barra. */
  minimoPureza: number | null;
  /** Nombre del producto principal de la reacción elegida. */
  producto: string;
  /** Datos medidos en el laboratorio: reemplazan a lo que estima el modelo. */
  medidos: Medidos;
  onMedidos: (m: Medidos) => void;
  incert: OpcionesIncertidumbre;
  onIncert: (o: OpcionesIncertidumbre) => void;
}

const colorDeValor = (v: number) => (v >= 75 ? 'var(--ok)' : v >= 50 ? 'var(--warn)' : 'var(--bad)');
const limitar = (v: number) => Math.max(0, Math.min(100, v));
const colorCategoria = (cat: string) =>
  cat === 'Excelente' || cat === 'Buena' ? 'var(--ok)' : cat === 'Regular' ? 'var(--warn)' : 'var(--bad)';

const ETIQUETA_ORIGEN = { estimacion: 'Estimación', mixto: 'Mixto', medido: 'Medido' } as const;
const EXPLICACION_ORIGEN = {
  estimacion: 'Todo sale de un modelo con parámetros sin validar: sirve para explorar, no para decidir.',
  mixto: 'Una parte son datos medidos y otra sigue siendo estimación del modelo.',
  medido: 'Rendimiento y pureza son datos medidos en el laboratorio.',
} as const;
const ESTADO_TEXTO = { cumple: 'Cumple', no_cumple: 'No cumple', sin_dato: 'Sin dato', sin_limite: 'Sin límite' } as const;
const GLOBAL_TEXTO: Record<CumplimientoGlobal, string> = {
  cumple: 'Cumple la especificación en todos los parámetros.',
  no_cumple: 'No cumple la especificación.',
  incompleto: 'Especificación incompleta: faltan mediciones o límites. No se puede afirmar que el producto cumpla.',
  sin_especificaciones: 'Este producto no tiene una especificación cargada.',
};

export function minimoDePureza(esp: Especificacion[]): number | null {
  const e = esp.find((x) => x.modelado) ?? esp.find((x) => x.parametro.toLowerCase().includes('pureza'));
  return e?.minimo ?? null;
}

const fmtIv = (iv: IntervaloMetrica, dec = 1) => `${iv.p5.toFixed(dec)} – ${iv.p95.toFixed(dec)}`;

function limiteTexto(e: EvaluacionEspecificacion): string {
  const u = e.unidad ? ` ${e.unidad}` : '';
  if (e.minimo !== null && e.maximo !== null) return `${e.minimo} – ${e.maximo}${u}`;
  if (e.minimo !== null) return `≥ ${e.minimo}${u}`;
  if (e.maximo !== null) return `≤ ${e.maximo}${u}`;
  return 'sin límite';
}

function Medidor({ valor }: { valor: number | null }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const p = valor === null ? 0 : valor / 100;
  return (
    <svg className="medidor" viewBox="0 0 120 120" role="img" aria-label="Puntaje de calidad">
      <circle cx={60} cy={60} r={r} fill="none" stroke="var(--pista)" strokeWidth={9} />
      <circle
        cx={60}
        cy={60}
        r={r}
        fill="none"
        stroke={valor === null ? 'var(--borde)' : colorDeValor(valor)}
        strokeWidth={9}
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - p)}
        transform="rotate(-90 60 60)"
        style={{ transition: 'stroke-dashoffset .6s, stroke .6s' }}
      />
      <text x={60} y={60} textAnchor="middle" dominantBaseline="central" className="medidor-num">
        {valor === null ? '--' : valor}
      </text>
    </svg>
  );
}

interface MetricaProps {
  etiqueta: string;
  valor: number;
  texto: string;
  sufijo?: string;
  /** Posición (0-100) de una marca, p. ej. la especificación mínima. */
  marca?: number | null;
  nota?: string;
  /** De dónde sale el dato: modelo (estimado) o experimental (medido). */
  origen?: 'modelo' | 'experimental';
  intervalo?: string;
}

function Metrica({ etiqueta, valor, texto, sufijo, marca, nota, origen, intervalo }: MetricaProps) {
  return (
    <div className="metrica">
      <div className="metrica-linea">
        <span>
          {etiqueta}
          {origen && <span className={`origen-tag ${origen}`}>{origen === 'modelo' ? 'estimado' : 'medido'}</span>}
        </span>
        <strong className="mono" style={{ color: colorDeValor(valor) }}>
          {texto}
          {sufijo && <small>{sufijo}</small>}
        </strong>
      </div>
      <div className="metrica-barra">
        <div style={{ width: `${limitar(valor)}%`, background: colorDeValor(valor) }} />
        {marca != null && <i style={{ left: `${limitar(marca)}%` }} />}
      </div>
      {intervalo && <span className="intervalo mono">{intervalo}</span>}
      {nota && <div className="metrica-nota">{nota}</div>}
    </div>
  );
}

function TablaEspecificaciones({
  resultado,
  medidos,
  onMedidos,
}: {
  resultado: Resultado;
  medidos: Medidos;
  onMedidos: (m: Medidos) => void;
}) {
  if (resultado.especificaciones.length === 0) {
    return <div className="global-spec sin_especificaciones">{GLOBAL_TEXTO.sin_especificaciones}</div>;
  }
  return (
    <>
      <h3 className="subtitulo">Especificación del producto</h3>
      <div className={`global-spec ${resultado.cumplimiento_especificaciones}`} role="status">
        {GLOBAL_TEXTO[resultado.cumplimiento_especificaciones]}
      </div>
      <table className="tabla-spec">
        <thead>
          <tr><th>Parámetro y límite</th><th className="num">Valor</th><th>Estado</th></tr>
        </thead>
        <tbody>
          {resultado.especificaciones.map((e) => (
            <tr key={e.id}>
              <td title={e.estado_limite}>
                {e.parametro}
                <div className="nota mono">{limiteTexto(e)}</div>
              </td>
              <td className="num mono">
                {e.modelado ? (
                  <>
                    {e.valor !== null ? e.valor.toFixed(1) : '—'}
                    <span className={`origen-tag ${e.origen === 'medido' ? 'medido' : 'modelo'}`}>{e.origen === 'medido' ? 'medido' : 'estimado'}</span>
                  </>
                ) : (
                  <CampoNumero
                    className="campo campo-num mono"
                    ariaLabel={`Medición de ${e.parametro}`}
                    placeholder="—"
                    min={0}
                    value={medidos.mediciones[e.id] ?? null}
                    onValor={(v) => {
                      const m = { ...medidos.mediciones };
                      if (v === null) delete m[e.id];
                      else m[e.id] = v;
                      onMedidos({ ...medidos, mediciones: m });
                    }}
                  />
                )}
              </td>
              <td><span className={`estado ${e.estado}`}>{ESTADO_TEXTO[e.estado]}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function BloqueIncertidumbre({
  resultado,
  incert,
  onIncert,
}: {
  resultado: Resultado | null;
  incert: OpcionesIncertidumbre;
  onIncert: (o: OpcionesIncertidumbre) => void;
}) {
  const inc = resultado?.incertidumbre ?? null;
  const num = (etiqueta: string, valor: number | null, set: (v: number | null) => void, unidad: string, opcional = false) => (
    <label className="fila-campo">
      <span>{etiqueta}</span>
      <CampoNumero
        className="campo campo-num mono"
        ariaLabel={etiqueta}
        placeholder={opcional ? '—' : undefined}
        min={0}
        value={valor}
        onValor={(v) => (opcional ? set(v) : v !== null && set(v))}
      />
      <span>{unidad}</span>
    </label>
  );
  return (
    <div className="bloque-medidas">
      <label className="casilla">
        <input type="checkbox" checked={incert.activa} onChange={(e) => onIncert({ ...incert, activa: e.target.checked })} />
        Calcular incertidumbre (Monte Carlo)
      </label>
      {incert.activa && (
        <div className="bloque-incert">
          {num('Error de cada pesada', incert.sdMasa, (v) => onIncert({ ...incert, sdMasa: v ?? 0 }), '% rel.')}
          {num('Error de pureza de insumos', incert.sdPureza, (v) => onIncert({ ...incert, sdPureza: v ?? 0 }), 'pts')}
          {num('Desvío del rendimiento', incert.sdRendimiento, (v) => onIncert({ ...incert, sdRendimiento: v }), 'pts', true)}
          {num('Error de la pureza del producto', incert.sdPurezaProducto, (v) => onIncert({ ...incert, sdPurezaProducto: v }), 'pts', true)}
          <p className="nota" style={{ margin: 0 }}>
            Los valores por defecto son supuestos: reemplazalos por los de tu balanza, los certificados y tus réplicas.
          </p>
        </div>
      )}
      {incert.activa && inc && (
        <>
          <table className="tabla-incert">
            <thead>
              <tr><th>{inc.corridas_validas} corridas</th><th>media</th><th>p5</th><th>p50</th><th>p95</th></tr>
            </thead>
            <tbody>
              {(
                [
                  ['Rendimiento (%)', inc.rendimiento_pct],
                  ['Pureza (%)', inc.pureza_producto_pct],
                  ['Producto (g)', inc.gramos_estimados],
                  ['Puntaje', inc.puntaje],
                ] as Array<[string, IntervaloMetrica]>
              ).map(([n, iv]) => (
                <tr key={n} className="mono">
                  <td>{n}</td><td>{iv.media}</td><td>{iv.p5}</td><td>{iv.p50}</td><td>{iv.p95}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="nota">
            Probabilidad de cumplir el mínimo de pureza: <strong className="mono">{(inc.prob_cumple_pureza * 100).toFixed(1)} %</strong>
            {!inc.incluye_incertidumbre_del_modelo && ' · no incluye el error del modelo'}
          </div>
          <ul className="notas-incert">
            {inc.notas.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

/** Panel de resultados: puntaje, métricas, producto estimado, alertas y detalle técnico. */
export function Resultados({ resultado, alertas, cargando, error, minimoPureza, producto, medidos, onMedidos, incert, onIncert }: Props) {
  const [detalle, setDetalle] = useState(false);
  // La barra de pureza muestra el rango 80–100 %.
  const aEscala = (p: number) => ((p - 80) / 20) * 100;
  const inc = resultado?.incertidumbre ?? null;

  return (
    <section className="panel resultados">
      <h2 className="titulo-panel grande">
        Resultados {cargando && <small className="cargando">calculando…</small>}
      </h2>

      {error && <div className="alerta bad">{error.startsWith('Error 4') ? error : `No se pudo contactar al backend. ${error}`}</div>}

      {resultado && (
        <div className="insignias">
          <span className={`insignia ${resultado.origen}`} data-testid="origen">{ETIQUETA_ORIGEN[resultado.origen]}</span>
          <span className="nota">{EXPLICACION_ORIGEN[resultado.origen]}</span>
        </div>
      )}
      {resultado && resultado.origen !== 'medido' && resultado.estado_validacion && (
        <p className="aviso-validacion">{resultado.estado_validacion}</p>
      )}

      <div className="puntaje">
        <Medidor valor={resultado ? resultado.puntaje : null} />
        <div>
          <div className="puntaje-cat" style={{ color: resultado ? colorCategoria(resultado.categoria) : 'var(--tenue)' }}>
            {resultado ? resultado.categoria : 'Sin datos'}
          </div>
          <div className="nota">Puntaje de calidad sobre 100</div>
          {inc && <div className="nota mono">entre {fmtIv(inc.puntaje, 0)} (p5–p95)</div>}
        </div>
      </div>

      {resultado ? (
        <>
          <div className="metricas">
            <Metrica
              etiqueta="Rendimiento"
              valor={resultado.rendimiento_pct}
              texto={`${resultado.rendimiento_pct.toFixed(1)}%`}
              origen={resultado.rendimiento_origen}
              intervalo={inc ? `${fmtIv(inc.rendimiento_pct)} % (p5–p95)` : undefined}
            />
            <Metrica
              etiqueta="Pureza"
              valor={aEscala(resultado.pureza_producto_pct)}
              texto={`${resultado.pureza_producto_pct.toFixed(1)}%`}
              marca={minimoPureza != null ? aEscala(minimoPureza) : null}
              nota={minimoPureza != null ? `mínimo ${minimoPureza}%` : undefined}
              origen={resultado.pureza_origen}
              intervalo={inc ? `${fmtIv(inc.pureza_producto_pct)} % (p5–p95)` : undefined}
            />
            <Metrica etiqueta="Balance" valor={resultado.balance_pct} texto={resultado.balance_pct.toFixed(0)} sufijo="/100" />
          </div>

          <div className="producto">
            <div className="nota">{producto} {resultado.rendimiento_origen === 'experimental' ? 'obtenido (según rendimiento medido)' : 'estimado'}</div>
            <div className="producto-valor mono">
              {resultado.gramos_estimados.toFixed(1)}
              <small>g</small>
            </div>
            <div className="nota">de {resultado.gramos_teoricos.toFixed(1)} g teóricos</div>
            {inc && <div className="nota mono">entre {fmtIv(inc.gramos_estimados)} g (p5–p95)</div>}
          </div>
        </>
      ) : (
        <p className="vacio">Agregá los reactivos de la reacción al reactor para ver el resultado.</p>
      )}

      {alertas.map((a, i) => (
        <div key={i} className={`alerta ${a.tipo}`}>
          {a.mensaje}
        </div>
      ))}

      {resultado && <TablaEspecificaciones resultado={resultado} medidos={medidos} onMedidos={onMedidos} />}

      <BloqueIncertidumbre resultado={resultado} incert={incert} onIncert={onIncert} />

      {resultado && (
        <>
          <button className="btn btn-contorno ancho desplegable" aria-expanded={detalle} onClick={() => setDetalle(!detalle)}>
            Ver detalle técnico <span>{detalle ? '▴' : '▾'}</span>
          </button>
          {detalle && (
            <table className="tabla">
              <tbody>
                <tr><td>Reactivo limitante</td><td>{resultado.reactivo_limitante}</td></tr>
                <tr><td>Peso molecular</td><td>{resultado.pm_producto} g/mol</td></tr>
                {resultado.pct_principio_activo !== null && (
                  <tr><td>% principio activo en mezcla</td><td>{resultado.pct_principio_activo.toFixed(1)}%</td></tr>
                )}
                <tr><td>Cumple pureza mínima</td><td>{resultado.cumple_pureza ? 'Sí' : 'No'}</td></tr>
                {resultado.economia_atomica_pct !== null && (
                  <tr><td>Economía atómica</td><td>{resultado.economia_atomica_pct.toFixed(1)}%</td></tr>
                )}
                {resultado.moles_reaccion !== null && (
                  <tr><td>Avance de la reacción</td><td className="mono">{resultado.moles_reaccion.toPrecision(4)} mol</td></tr>
                )}
                <tr><td>Ecuación</td><td className="mono"><Formula texto={resultado.ecuacion} /></td></tr>
              </tbody>
            </table>
          )}
          {detalle && (
            <table className="tabla multi">
              <thead>
                <tr><th>Reactivo</th><th>Cargado</th><th>Consumido</th><th>Sobra</th></tr>
              </thead>
              <tbody>
                {resultado.reactivos.map((x) => (
                  <tr key={x.id}>
                    <td>{x.nombre}{x.limitante ? ' (limitante)' : ''}{x.fraccion_soluto < 1 ? ` · solución ${(x.fraccion_soluto * 100).toFixed(1)} %` : ''}</td>
                    <td className="mono">{x.gramos_cargados.toFixed(2)} g</td>
                    <td className="mono">{x.gramos_consumidos.toFixed(2)} g</td>
                    <td className="mono">{x.gramos_sobrantes.toFixed(2)} g</td>
                  </tr>
                ))}
              </tbody>
              <thead>
                <tr><th>Producto</th><th>Teórico</th><th>Estimado</th><th /></tr>
              </thead>
              <tbody>
                {resultado.productos.map((x) => (
                  <tr key={x.id}>
                    <td>{x.nombre}{x.principal ? ' (principal)' : ''}</td>
                    <td className="mono">{x.gramos_teoricos.toFixed(2)} g</td>
                    <td className="mono">{x.gramos_estimados.toFixed(2)} g</td>
                    <td />
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {detalle && (
            <div className="bloque-medidas">
              <h3 className="subtitulo" style={{ margin: 0 }}>Datos medidos</h3>
              <label className="fila-campo" title="Una o varias réplicas separadas por coma: con dos o más se calcula el desvío entre réplicas">
                <span>Rendimiento medido (réplicas separadas por coma)</span>
                <input
                  className="campo mono"
                  aria-label="Rendimiento medido"
                  placeholder="78, 82, 80"
                  value={medidos.rendimiento}
                  onChange={(e) => onMedidos({ ...medidos, rendimiento: e.target.value })}
                />
                <span>%</span>
              </label>
              <label className="fila-campo">
                <span>Pureza del producto medida</span>
                <CampoNumero
                  className="campo campo-num mono"
                  ariaLabel="Pureza medida"
                  placeholder="—"
                  min={0}
                  max={100}
                  value={medidos.pureza}
                  onValor={(v) => onMedidos({ ...medidos, pureza: v === null ? null : Math.min(100, Math.max(0, v)) })}
                />
                <span>%</span>
              </label>
            </div>
          )}
        </>
      )}
    </section>
  );
}
