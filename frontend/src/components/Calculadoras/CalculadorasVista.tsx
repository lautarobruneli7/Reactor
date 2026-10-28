import { useState, type FormEvent } from 'react';
import { balancear, calcularPM, convertirConcentracion, convertirUnidades } from '../../api/client';
import type {
  Compuesto,
  Concentracion,
  RespuestaBalanceo,
  RespuestaConcentracion,
  RespuestaConversion,
  RespuestaPM,
  TipoConcentracion,
  UnidadCantidad,
} from '../../types';
import { UNIDADES } from '../../types';
import { Formula } from '../Compuestos/categorias';
import { CampoNumero } from '../Controles/CampoNumero';

type Herramienta = 'pm' | 'balanceo' | 'unidades' | 'soluciones';

const HERRAMIENTAS: Array<[Herramienta, string]> = [
  ['pm', 'Peso molecular'],
  ['balanceo', 'Balanceo de ecuaciones'],
  ['unidades', 'Conversión de unidades'],
  ['soluciones', 'Concentración de soluciones'],
];

const TIPOS: Array<[TipoConcentracion, string]> = [
  ['p/p', '% p/p (masa)'],
  ['p/v', '% p/v (g/100 mL)'],
  ['molar', 'mol/L (molar)'],
];

const sinAcentoError = (e: unknown) => (e instanceof Error ? e.message.replace(/^Error \d+: /, '') : 'Error desconocido');
const num = (n: number | null, dec = 4) => (n === null ? '—' : Number(n.toPrecision(dec)).toString());

function Error_({ texto }: { texto: string | null }) {
  return texto ? <div className="alerta bad error-calc" role="alert">{texto}</div> : null;
}

// ---------------------------------------------------------------- peso molecular
function PesoMolecular() {
  const [formula, setFormula] = useState('C13H18O2');
  const [res, setRes] = useState<RespuestaPM | null>(null);
  const [error, setError] = useState<string | null>(null);

  const calcular = (e?: FormEvent, f = formula) => {
    e?.preventDefault();
    setError(null);
    calcularPM(f)
      .then(setRes)
      .catch((x: unknown) => {
        setRes(null);
        setError(sinAcentoError(x));
      });
  };

  return (
    <section className="panel">
      <h2 className="titulo-panel grande">Peso molecular y composición</h2>
      <p className="nota">Sirve para cualquier fórmula, no solo las del catálogo. Admite paréntesis e hidratos (CuSO4·5H2O).</p>
      <form className="form-calc" onSubmit={calcular}>
        <label className="ancho-total">
          Fórmula
          <input className="campo mono" aria-label="Fórmula" value={formula} onChange={(e) => setFormula(e.target.value)} />
        </label>
        <div className="acciones">
          <button className="btn btn-primario" type="submit">Calcular</button>
          {['C13H18O2', 'CuSO4·5H2O', 'Ca(OH)2'].map((f) => (
            <button key={f} type="button" className="btn btn-contorno" onClick={() => { setFormula(f); calcular(undefined, f); }}>
              {f}
            </button>
          ))}
        </div>
      </form>
      <Error_ texto={error} />
      {res && (
        <div className="resultado-calc">
          <div className="grande-num mono" data-testid="pm">{res.pm} <small style={{ fontSize: 14, color: 'var(--tenue)' }}>g/mol</small></div>
          <div className="nota">Fórmula de Hill: <span className="mono"><Formula texto={res.formula_hill} /></span></div>
          <table className="tabla">
            <tbody>
              {res.composicion.map((c) => (
                <tr key={c.simbolo}>
                  <td className="mono">{c.simbolo}</td>
                  <td>{c.atomos} {c.atomos === 1 ? 'átomo' : 'átomos'}</td>
                  <td className="mono">{c.masa_pct.toFixed(2)} %</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- balanceo
const partir = (t: string) => t.split(/[,;+]/).map((x) => x.trim()).filter(Boolean);

function Balanceo() {
  const [reactivos, setReactivos] = useState('C3H8, O2');
  const [productos, setProductos] = useState('CO2, H2O');
  const [res, setRes] = useState<RespuestaBalanceo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const calcular = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    balancear(partir(reactivos), partir(productos))
      .then(setRes)
      .catch((x: unknown) => {
        setRes(null);
        setError(sinAcentoError(x));
      });
  };

  const masa = (l: RespuestaBalanceo['reactivos']) => l.reduce((s, x) => s + x.gramos_por_mol_de_reaccion, 0);

  return (
    <section className="panel">
      <h2 className="titulo-panel grande">Balanceo de ecuaciones</h2>
      <p className="nota">Escribí las fórmulas separadas por coma. Se balancea por conservación de átomos, con aritmética exacta.</p>
      <form className="form-calc" onSubmit={calcular}>
        <label>
          Reactivos
          <input className="campo mono" aria-label="Reactivos" value={reactivos} onChange={(e) => setReactivos(e.target.value)} />
        </label>
        <label>
          Productos
          <input className="campo mono" aria-label="Productos" value={productos} onChange={(e) => setProductos(e.target.value)} />
        </label>
        <button className="btn btn-primario" type="submit">Balancear</button>
      </form>
      <Error_ texto={error} />
      {res && (
        <div className="resultado-calc">
          <div className="grande-num mono" data-testid="ecuacion"><Formula texto={res.ecuacion} /></div>
          <table className="tabla multi">
            <thead>
              <tr><th>Especie</th><th>Coef.</th><th>PM (g/mol)</th><th>g por mol de reacción</th></tr>
            </thead>
            <tbody>
              {[...res.reactivos, ...res.productos].map((x, i) => (
                <tr key={`${x.formula}-${i}`}>
                  <td className="mono"><Formula texto={x.formula} /></td>
                  <td className="mono">{x.coef}</td>
                  <td className="mono">{x.pm}</td>
                  <td className="mono">{x.gramos_por_mol_de_reaccion}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="nota">
            Masa que entra: {masa(res.reactivos).toFixed(3)} g · masa que sale: {masa(res.productos).toFixed(3)} g (por mol de reacción).
          </p>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- unidades
function Unidades({ catalogo }: { catalogo: Compuesto[] }) {
  const [compuestoId, setCompuestoId] = useState('etanol');
  const [cantidad, setCantidad] = useState<number>(100);
  const [unidad, setUnidad] = useState<UnidadCantidad>('mL');
  const [aUnidad, setAUnidad] = useState<UnidadCantidad>('mol');
  const [pureza, setPureza] = useState<number>(100);
  const [solucion, setSolucion] = useState(false);
  const [concentracion, setConcentracion] = useState<Concentracion>({ tipo: 'p/p', valor: 37 });
  const [densidad, setDensidad] = useState<number | null>(null);
  const [res, setRes] = useState<RespuestaConversion | null>(null);
  const [error, setError] = useState<string | null>(null);

  const calcular = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    convertirUnidades({
      compuestoId, cantidad, unidad, aUnidad, pureza,
      concentracion: solucion ? concentracion : null,
      densidad,
    })
      .then(setRes)
      .catch((x: unknown) => {
        setRes(null);
        setError(sinAcentoError(x));
      });
  };

  return (
    <section className="panel">
      <h2 className="titulo-panel grande">Conversión de unidades</h2>
      <p className="nota">
        Entre masa, volumen y moles. Los moles son netos del compuesto (descuentan pureza y concentración). Para pasar de volumen a
        masa hace falta la densidad: la del catálogo (líquidos puros) o la que informes.
      </p>
      <form className="form-calc" onSubmit={calcular}>
        <label className="ancho-total">
          Compuesto
          <select className="campo" aria-label="Compuesto" value={compuestoId} onChange={(e) => setCompuestoId(e.target.value)}>
            {catalogo.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
        </label>
        <label>
          Cantidad
          <CampoNumero className="campo mono" ariaLabel="Cantidad" min={0} value={cantidad} onValor={(v) => v !== null && setCantidad(v)} />
        </label>
        <label>
          De
          <select className="campo" aria-label="De" value={unidad} onChange={(e) => setUnidad(e.target.value as UnidadCantidad)}>
            {UNIDADES.map((u) => <option key={u}>{u}</option>)}
          </select>
        </label>
        <label>
          A
          <select className="campo" aria-label="A" value={aUnidad} onChange={(e) => setAUnidad(e.target.value as UnidadCantidad)}>
            {UNIDADES.map((u) => <option key={u}>{u}</option>)}
          </select>
        </label>
        <label>
          Pureza (%)
          <CampoNumero className="campo mono" ariaLabel="Pureza" min={0} max={100} value={pureza} onValor={(v) => v !== null && setPureza(Math.min(100, Math.max(0, v)))} />
        </label>
        <label className="casilla">
          <input type="checkbox" checked={solucion} onChange={(e) => setSolucion(e.target.checked)} aria-label="En solución" />
          En solución
        </label>
        {solucion && (
          <>
            <label>
              Concentración
              <CampoNumero className="campo mono" ariaLabel="Concentración" min={0} value={concentracion.valor} onValor={(v) => v !== null && v > 0 && setConcentracion({ ...concentracion, valor: v })} />
            </label>
            <label>
              Tipo
              <select className="campo" aria-label="Tipo de concentración" value={concentracion.tipo} onChange={(e) => setConcentracion({ ...concentracion, tipo: e.target.value as TipoConcentracion })}>
                {TIPOS.map(([t, n]) => <option key={t} value={t}>{n}</option>)}
              </select>
            </label>
          </>
        )}
        <label>
          Densidad (g/mL, opcional)
          <CampoNumero className="campo mono" ariaLabel="Densidad" min={0} placeholder="catálogo" value={densidad} onValor={(v) => setDensidad(v !== null && v > 0 ? v : null)} />
        </label>
        <button className="btn btn-primario" type="submit">Convertir</button>
      </form>
      <Error_ texto={error} />
      {res && (
        <div className="resultado-calc">
          <div className="grande-num mono" data-testid="conversion">{num(res.valor)} {res.unidad}</div>
          <table className="tabla">
            <tbody>
              <tr><td>Masa de material</td><td className="mono">{num(res.gramos_material)} g</td></tr>
              <tr><td>Fracción de la masa que es el compuesto</td><td className="mono">{num(res.fraccion_soluto * 100)} %</td></tr>
              <tr><td>Masa neta del compuesto</td><td className="mono">{num(res.gramos_compuesto_neto)} g</td></tr>
              <tr><td>Moles netos</td><td className="mono">{num(res.moles_netos)} mol</td></tr>
              {res.densidad_g_ml !== null && <tr><td>Densidad usada</td><td className="mono">{res.densidad_g_ml} g/mL</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- soluciones
function Soluciones({ catalogo }: { catalogo: Compuesto[] }) {
  const [porFormula, setPorFormula] = useState(false);
  const [compuestoId, setCompuestoId] = useState('hcl');
  const [formula, setFormula] = useState('NaCl');
  const [concentracion, setConcentracion] = useState<Concentracion>({ tipo: 'p/p', valor: 37 });
  const [densidad, setDensidad] = useState<number | null>(1.18);
  const [res, setRes] = useState<RespuestaConcentracion | null>(null);
  const [error, setError] = useState<string | null>(null);

  const calcular = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    convertirConcentracion(concentracion, porFormula ? { formula } : { compuestoId }, densidad)
      .then(setRes)
      .catch((x: unknown) => {
        setRes(null);
        setError(sinAcentoError(x));
      });
  };

  return (
    <section className="panel">
      <h2 className="titulo-panel grande">Concentración de soluciones</h2>
      <p className="nota">
        Expresa una concentración como % p/p, % p/v y molar. Salvo desde % p/p, hace falta la densidad de la solución: el programa no la
        inventa (está en la etiqueta del frasco o en el certificado).
      </p>
      <form className="form-calc" onSubmit={calcular}>
        <label className="casilla ancho-total">
          <input type="checkbox" checked={porFormula} onChange={(e) => setPorFormula(e.target.checked)} aria-label="Usar una fórmula" />
          Usar una fórmula en lugar de un compuesto del catálogo
        </label>
        {porFormula ? (
          <label className="ancho-total">
            Fórmula del soluto
            <input className="campo mono" aria-label="Fórmula del soluto" value={formula} onChange={(e) => setFormula(e.target.value)} />
          </label>
        ) : (
          <label className="ancho-total">
            Soluto
            <select className="campo" aria-label="Soluto" value={compuestoId} onChange={(e) => setCompuestoId(e.target.value)}>
              {catalogo.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
          </label>
        )}
        <label>
          Concentración
          <CampoNumero className="campo mono" ariaLabel="Concentración" min={0} value={concentracion.valor} onValor={(v) => v !== null && v > 0 && setConcentracion({ ...concentracion, valor: v })} />
        </label>
        <label>
          Tipo
          <select className="campo" aria-label="Tipo de concentración" value={concentracion.tipo} onChange={(e) => setConcentracion({ ...concentracion, tipo: e.target.value as TipoConcentracion })}>
            {TIPOS.map(([t, n]) => <option key={t} value={t}>{n}</option>)}
          </select>
        </label>
        <label>
          Densidad de la solución (g/mL)
          <CampoNumero className="campo mono" ariaLabel="Densidad de la solución" min={0} value={densidad} onValor={(v) => setDensidad(v !== null && v > 0 ? v : null)} />
        </label>
        <button className="btn btn-primario" type="submit">Convertir</button>
      </form>
      <Error_ texto={error} />
      {res && (
        <div className="resultado-calc">
          <table className="tabla">
            <tbody>
              <tr><td>% p/p (masa)</td><td className="mono" data-testid="pp">{num(res.p_p_pct)} %</td></tr>
              <tr><td>% p/v (g/100 mL)</td><td className="mono">{num(res.p_v_pct)}</td></tr>
              <tr><td>Molaridad</td><td className="mono" data-testid="molar">{num(res.molar)} mol/L</td></tr>
              <tr><td>g de soluto por litro</td><td className="mono">{num(res.g_por_l)}</td></tr>
              <tr><td>Peso molecular usado</td><td className="mono">{num(res.pm)} g/mol</td></tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/** Calculadoras que no dependen de una reacción: peso molecular, balanceo, unidades y soluciones. */
export function CalculadorasVista({ catalogo }: { catalogo: Compuesto[] }) {
  const [activa, setActiva] = useState<Herramienta>('pm');
  const liquidosYSolutos = catalogo.filter((c) => c.pm_aplicable);
  return (
    <div className="vista-calc">
      <nav className="menu-calc" aria-label="Calculadoras">
        {HERRAMIENTAS.map(([id, nombre]) => (
          <button key={id} className={activa === id ? 'activa' : ''} aria-pressed={activa === id} onClick={() => setActiva(id)}>
            {nombre}
          </button>
        ))}
      </nav>
      <div>
        {activa === 'pm' && <PesoMolecular />}
        {activa === 'balanceo' && <Balanceo />}
        {activa === 'unidades' && <Unidades catalogo={liquidosYSolutos} />}
        {activa === 'soluciones' && <Soluciones catalogo={liquidosYSolutos} />}
      </div>
    </div>
  );
}
