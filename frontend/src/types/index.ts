// Tipos que reflejan los esquemas del backend (backend/app/models/schemas.py).

export type TipoCompuesto = 'reactivo' | 'catalizador' | 'excipiente' | 'solvente' | 'principio_activo';
export type FaseCompuesto = 'líquido' | 'sólido' | 'gas';

export interface Compuesto {
  id: string;
  nombre: string;
  rol: string;
  tipo: TipoCompuesto;
  /** Categoría de la biblioteca (Ácidos, Solventes, Gases...). */
  categoria: string;
  fase: FaseCompuesto;
  /** g/mol; 0 si no aplica (polímeros). */
  pm: number;
  pm_aplicable: boolean;
  smiles: string | null;
  formula: string | null;
  cas: string | null;
  tm_c: number | null;
  tb_c: number | null;
  sinonimos: string[];
  nota: string;
  /** "controlado" = sustancia fiscalizada (RENPRE); ver `regulacion`. */
  acceso: 'libre' | 'controlado';
  regulacion: string | null;
  /** false si fórmula y peso molecular no se pudieron contrastar con la base pública. */
  verificado: boolean;
  fuente: string;
}

export interface ParticipanteReaccion {
  id: string;
  coef: number;
  principal?: boolean;
}

export interface Reaccion {
  id: string;
  nombre: string;
  descripcion: string;
  categoria: string;
  reactivos: ParticipanteReaccion[];
  productos: ParticipanteReaccion[];
  catalizador: string | null;
  excipiente: string | null;
  ecuacion: string;
  balanceada: boolean;
  estado_validacion: string;
}

export type UnidadCantidad = 'g' | 'kg' | 'mg' | 'mL' | 'L' | 'mol' | 'mmol';
export const UNIDADES: UnidadCantidad[] = ['g', 'kg', 'mg', 'mL', 'L', 'mol', 'mmol'];

export type TipoConcentracion = 'p/p' | 'p/v' | 'molar';
export interface Concentracion {
  tipo: TipoConcentracion;
  valor: number;
}

/**
 * Un compuesto ya colocado en el reactor, con sus cantidades.
 *
 * `pureza` y `concentracion` son datos distintos: la pureza es cuánto del compuesto es el compuesto buscado;
 * la concentración es cuánto de la masa es el compuesto cuando viene en solución (HCl 37 % p/p).
 */
export interface ComponenteEnReactor {
  uid: number;
  id: string;
  /** Cantidad en la unidad elegida; si la unidad es 'g', son los gramos. */
  cantidad: number;
  unidad: UnidadCantidad;
  pureza: number;
  concentracion: Concentracion | null;
  /** Densidad (g/mL) del material tal como se carga; hace falta para mL/L de una solución, %p/v y molar. */
  densidad: number | null;
}

export type TipoAlerta = 'ok' | 'warn' | 'bad' | 'info';

export interface Alerta {
  tipo: TipoAlerta;
  mensaje: string;
}

export type EstadoEspecificacion = 'cumple' | 'no_cumple' | 'sin_dato' | 'sin_limite';
export type CumplimientoGlobal = 'cumple' | 'no_cumple' | 'incompleto' | 'sin_especificaciones';

export interface EvaluacionEspecificacion {
  id: string;
  parametro: string;
  unidad: string;
  minimo: number | null;
  maximo: number | null;
  valor: number | null;
  origen: 'modelo' | 'medido' | null;
  estado: EstadoEspecificacion;
  modelado: boolean;
  fuente: string;
  estado_limite: string;
}

export interface IntervaloMetrica {
  media: number;
  sd: number;
  p5: number;
  p50: number;
  p95: number;
}

export interface Incertidumbre {
  metodo: string;
  n: number;
  corridas_validas: number;
  semilla: number;
  supuestos: Record<string, number | null>;
  incluye_incertidumbre_del_modelo: boolean;
  rendimiento_pct: IntervaloMetrica;
  pureza_producto_pct: IntervaloMetrica;
  gramos_estimados: IntervaloMetrica;
  puntaje: IntervaloMetrica;
  prob_cumple_pureza: number;
  notas: string[];
}

export interface CargaResuelta {
  id: string;
  gramos_material: number;
  fraccion_soluto: number;
  moles_netos: number | null;
}

export type OrigenDato = 'modelo' | 'experimental';

export interface Resultado {
  puntaje: number;
  categoria: string;
  rendimiento_pct: number;
  pureza_producto_pct: number;
  balance_pct: number;
  reactivo_limitante: string;
  gramos_teoricos: number;
  gramos_estimados: number;
  pm_producto: number;
  pct_principio_activo: number | null;
  cumple_pureza: boolean;
  reaccion_id: string;
  reaccion_nombre: string;
  ecuacion: string;
  economia_atomica_pct: number | null;
  moles_reaccion: number | null;
  /** "experimental" si el dato lo informó el usuario en lugar de estimarlo el modelo. */
  rendimiento_origen: OrigenDato;
  pureza_origen: OrigenDato;
  /** estimacion = todo sale del modelo; mixto = algún dato medido; medido = rendimiento y pureza medidos. */
  origen: 'estimacion' | 'mixto' | 'medido';
  estado_validacion: string;
  reactivos: Array<{
    id: string; nombre: string; coef: number; gramos_cargados: number; moles_utiles: number;
    exceso_pct: number; gramos_consumidos: number; gramos_sobrantes: number; limitante: boolean;
    fraccion_soluto: number;
  }>;
  productos: Array<{
    id: string; nombre: string; coef: number; principal: boolean; pm: number;
    gramos_teoricos: number; gramos_estimados: number;
  }>;
  cargas: CargaResuelta[];
  especificaciones: EvaluacionEspecificacion[];
  cumplimiento_especificaciones: CumplimientoGlobal;
  incertidumbre: Incertidumbre | null;
}

export interface SimulacionSalida {
  resultado: Resultado | null;
  alertas: Alerta[];
}

export interface Especificacion {
  id: string;
  producto: string;
  parametro: string;
  minimo: number | null;
  maximo: number | null;
  unidad: string;
  fuente: string;
  estado: string;
  modelado: boolean;
  tipo: string;
  farmacopea: string;
}

/** Datos medidos en el laboratorio que reemplazan a la estimación del modelo. */
export interface Medidos {
  /** Uno o varios rendimientos (%) separados por coma o espacio; con 2 o más se calcula el desvío entre réplicas. */
  rendimiento: string;
  /** Pureza del producto medida (%), p. ej. por HPLC. */
  pureza: number | null;
  /** Resultados por id de especificación (pérdida por secado, metales pesados...). */
  mediciones: Record<string, number>;
}

export const SIN_MEDIDOS: Medidos = { rendimiento: '', pureza: null, mediciones: {} };

export interface OpcionesIncertidumbre {
  activa: boolean;
  n: number;
  sdMasa: number;
  sdPureza: number;
  sdRendimiento: number | null;
  sdPurezaProducto: number | null;
}

export const INCERTIDUMBRE_INICIAL: OpcionesIncertidumbre = {
  activa: false,
  n: 1000,
  sdMasa: 0.5,
  sdPureza: 0.5,
  sdRendimiento: null,
  sdPurezaProducto: null,
};

/** Un componente tal como se guarda en un ensayo. */
export type ComponenteGuardado = Pick<ComponenteEnReactor, 'id' | 'cantidad' | 'unidad' | 'pureza' | 'concentracion' | 'densidad'>;

/** Un ensayo guardado: la mezcla y una foto de sus resultados. */
export interface Ensayo {
  numero: number;
  fecha: string;
  /** Reacción con la que se hizo el ensayo (los guardados antes no la traen: era el ibuprofeno). */
  reaccion_id?: string;
  componentes: ComponenteGuardado[];
  medidos?: Medidos;
  puntaje: number | null;
  categoria: string | null;
  rendimiento_pct: number | null;
  pureza_producto_pct: number | null;
  origen?: 'estimacion' | 'mixto' | 'medido';
}

// ---------- Tabla periódica y calculadoras ----------
export interface Elemento {
  numero: number;
  simbolo: string;
  nombre: string;
  nombre_en: string;
  masa_atomica: number;
  grupo: number | null;
  periodo: number;
  categoria: string;
  fase_25c: FaseCompuesto | null;
  radiactivo: boolean;
  fuente: string;
}

export interface ComposicionElemental {
  simbolo: string;
  atomos: number;
  masa_pct: number;
}

export interface RespuestaPM {
  formula: string;
  formula_hill: string;
  pm: number;
  composicion: ComposicionElemental[];
}

export interface EspecieBalanceada {
  formula: string;
  coef: number;
  pm: number;
  gramos_por_mol_de_reaccion: number;
}

export interface RespuestaBalanceo {
  ecuacion: string;
  reactivos: EspecieBalanceada[];
  productos: EspecieBalanceada[];
}

export interface RespuestaConversion {
  compuesto_id: string;
  valor: number;
  unidad: UnidadCantidad;
  gramos_material: number;
  fraccion_soluto: number;
  gramos_compuesto_neto: number;
  moles_netos: number | null;
  densidad_g_ml: number | null;
}

export interface RespuestaConcentracion {
  pm: number;
  p_p_pct: number;
  p_v_pct: number | null;
  molar: number | null;
  g_por_l: number | null;
  fraccion_masica: number;
  densidad_g_ml: number | null;
}

// ---------- Usuarios, ensayos del servidor y auditoría ----------
export type Rol = 'lectura' | 'analista' | 'calidad' | 'admin';
export const NIVEL_ROL: Record<Rol, number> = { lectura: 1, analista: 2, calidad: 3, admin: 4 };
export const alcanzaRol = (rol: Rol | undefined, minimo: Rol) => (rol ? NIVEL_ROL[rol] >= NIVEL_ROL[minimo] : false);

export interface Usuario {
  id: number;
  email: string;
  nombre: string;
  rol: Rol;
  activo: boolean;
  creado_en: string;
}

export interface Sistema {
  version: string;
  auth_activa: boolean;
  base: string;
  rdkit: boolean;
}

export type EstadoEnsayo = 'registrado' | 'revisado' | 'aprobado' | 'rechazado';
export type TipoEvento = 'comentario' | 'revisado' | 'aprobado' | 'rechazado';

export interface EnsayoResumen {
  id: number;
  creado_en: string;
  usuario_id: number;
  usuario: string;
  reaccion_id: string;
  reaccion_nombre: string;
  lote: string | null;
  estado: EstadoEnsayo;
  corrige_a: number | null;
  reemplazado_por: number | null;
  vigente: boolean;
  version_modelo: string;
  puntaje: number | null;
  categoria: string | null;
  rendimiento_pct: number | null;
  pureza_producto_pct: number | null;
  gramos_estimados: number | null;
  origen: 'estimacion' | 'mixto' | 'medido' | null;
  cumplimiento_especificaciones: string | null;
  /** Última decisión (revisado, aprobado o rechazado); null si todavía no hubo ninguna. */
  revision_por: string | null;
  revision_en: string | null;
  revision_comentario: string | null;
  n_comentarios: number;
}

/** Contadores del panel de aceptación. Los cuatro estados cuentan solo ensayos vigentes; `total` incluye también los reemplazados. */
export interface ConteoEstados {
  registrado: number;
  revisado: number;
  aprobado: number;
  rechazado: number;
  reemplazados: number;
  total: number;
}

export interface EventoEnsayo {
  id: number;
  tipo: TipoEvento;
  usuario_id: number;
  usuario: string;
  creado_en: string;
  comentario: string;
}

export interface EntradaGuardada {
  componentes: Array<{
    id: string;
    gramos: number | null;
    cantidad: number | null;
    unidad: UnidadCantidad;
    pureza: number;
    concentracion: Concentracion | null;
    densidad_g_ml: number | null;
  }>;
  reaccion_id: string;
  rendimiento_real_pct: number | null;
  rendimiento_replicas_pct: number[] | null;
  pureza_real_pct: number | null;
  mediciones: Record<string, number>;
}

export interface EnsayoServidor extends EnsayoResumen {
  notas: string;
  entrada: EntradaGuardada;
  salida: SimulacionSalida;
  eventos: EventoEnsayo[];
  digest: string;
  sello: { id: number; hash: string; prev_hash: string; creado_en: string } | null;
}

export interface FiltroEnsayos {
  lote: string;
  estado: '' | EstadoEnsayo;
  soloVigentes: boolean;
  pagina: number;
}

export interface ComparacionEnsayos {
  ensayos: EnsayoResumen[];
  compuestos: Array<{ id: string; gramos: Record<string, number> }>;
  metricas: Array<{ metrica: string; valores: Record<string, string | number | null> }>;
}

export interface RegistroAuditoria {
  id: number;
  creado_en: string;
  usuario_id: number | null;
  usuario: string | null;
  accion: string;
  entidad: string;
  entidad_id: number | null;
  detalle: Record<string, unknown>;
  prev_hash: string;
  hash: string;
}

export interface VerificacionAuditoria {
  ok: boolean;
  registros: number;
  ensayos_verificados: number;
  eventos_verificados: number;
  ultimo_hash: string;
  total_errores: number;
  errores: Array<{ registro_id: number | null; motivo: string }>;
}
