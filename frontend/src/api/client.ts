import type {
  ComparacionEnsayos,
  ComponenteEnReactor,
  Compuesto,
  Concentracion,
  ConteoEstados,
  Elemento,
  EnsayoResumen,
  EnsayoServidor,
  Especificacion,
  EstadoEnsayo,
  Medidos,
  OpcionesIncertidumbre,
  Reaccion,
  RespuestaBalanceo,
  RespuestaConcentracion,
  RespuestaConversion,
  RegistroAuditoria,
  RespuestaPM,
  Rol,
  SimulacionSalida,
  Sistema,
  TipoEvento,
  UnidadCantidad,
  Usuario,
  VerificacionAuditoria,
} from '../types';
import { parsearRendimiento } from '../utilidades/cargas';

const BASE = import.meta.env.VITE_API_URL ?? '/api';

// ---------- Sesión ----------
// El token vive en sessionStorage: se pierde al cerrar la pestaña (no queda guardado en el disco del navegador).
const CLAVE_TOKEN = 'retorta.token';
const escuchas = new Set<() => void>();

export const leerToken = (): string | null => {
  try {
    return sessionStorage.getItem(CLAVE_TOKEN);
  } catch {
    return null;
  }
};
export const guardarToken = (t: string | null) => {
  try {
    if (t) sessionStorage.setItem(CLAVE_TOKEN, t);
    else sessionStorage.removeItem(CLAVE_TOKEN);
  } catch {
    /* almacenamiento bloqueado: la sesión dura lo que dure la página */
  }
};
/** Avisa cuando el servidor responde 401 (sesión vencida), para volver a la pantalla de ingreso. */
export const alVencerSesion = (f: () => void) => {
  escuchas.add(f);
  return () => void escuchas.delete(f);
};

function cabeceras(extra?: HeadersInit): Headers {
  const h = new Headers({ 'Content-Type': 'application/json' });
  const t = leerToken();
  if (t) h.set('Authorization', `Bearer ${t}`);
  new Headers(extra).forEach((v, k) => h.set(k, v));
  return h;
}

async function textoDeError(r: Response): Promise<string> {
  let detalle = r.statusText;
  try {
    const j = await r.json();
    if (typeof j.detail === 'string') detalle = j.detail;
    else if (Array.isArray(j.detail)) detalle = j.detail.map((d: { msg?: string }) => d.msg ?? '').filter(Boolean).join('; ');
  } catch {
    /* respuesta sin JSON */
  }
  return `Error ${r.status}: ${detalle}`;
}

async function pedirConCabeceras<T>(ruta: string, init?: RequestInit): Promise<{ datos: T; cabeceras: Headers }> {
  const r = await fetch(`${BASE}${ruta}`, { ...init, headers: cabeceras(init?.headers) });
  if (r.status === 401 && leerToken()) {
    guardarToken(null);
    escuchas.forEach((f) => f());
  }
  if (!r.ok) throw new Error(await textoDeError(r));
  return { datos: (await r.json()) as T, cabeceras: r.headers };
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  return (await pedirConCabeceras<T>(ruta, init)).datos;
}

export function obtenerCompuestos(): Promise<Compuesto[]> {
  return pedir<Compuesto[]>('/compuestos');
}

export function obtenerReacciones(): Promise<Reaccion[]> {
  return pedir<Reaccion[]>('/reacciones');
}

export interface PedidoSimulacion {
  componentes: ComponenteEnReactor[];
  reaccionId: string;
  medidos: Medidos;
  incertidumbre: OpcionesIncertidumbre;
}

/** Arma el cuerpo de POST /api/simulacion: con unidad "g" va como `gramos`, con otra como `cantidad` + `unidad`. */
export function cuerpoSimulacion({ componentes, reaccionId, medidos, incertidumbre }: PedidoSimulacion): Record<string, unknown> {
  const rend = parsearRendimiento(medidos.rendimiento);
  return {
    componentes: componentes.map((c) => ({
      id: c.id,
      ...(c.unidad === 'g' ? { gramos: c.cantidad } : { cantidad: c.cantidad, unidad: c.unidad }),
      pureza: c.pureza,
      concentracion: c.concentracion,
      densidad_g_ml: c.densidad,
    })),
    reaccion_id: reaccionId,
    rendimiento_real_pct: rend.length === 1 ? rend[0] : null,
    rendimiento_replicas_pct: rend.length >= 2 ? rend : null,
    pureza_real_pct: medidos.pureza,
    mediciones: medidos.mediciones,
    incertidumbre: incertidumbre.activa
      ? {
          n: incertidumbre.n,
          sd_masa_rel_pct: incertidumbre.sdMasa,
          sd_pureza_pts: incertidumbre.sdPureza,
          sd_rendimiento_pts: incertidumbre.sdRendimiento,
          sd_pureza_producto_pts: incertidumbre.sdPurezaProducto,
        }
      : null,
  };
}

export function simular(pedido: PedidoSimulacion, signal?: AbortSignal): Promise<SimulacionSalida> {
  return pedir<SimulacionSalida>('/simulacion', { method: 'POST', signal, body: JSON.stringify(cuerpoSimulacion(pedido)) });
}

export function obtenerEspecificaciones(): Promise<Especificacion[]> {
  return pedir<Especificacion[]>('/especificaciones');
}

export function obtenerPropiedades(id: string): Promise<Record<string, number | string>> {
  return pedir<Record<string, number | string>>(`/compuestos/${id}/propiedades`);
}

// ---------- Tabla periódica y calculadoras ----------
export function obtenerElementos(): Promise<Elemento[]> {
  return pedir<Elemento[]>('/elementos');
}

export function calcularPM(formula: string): Promise<RespuestaPM> {
  return pedir<RespuestaPM>(`/formulas/pm?formula=${encodeURIComponent(formula)}`);
}

export function balancear(reactivos: string[], productos: string[]): Promise<RespuestaBalanceo> {
  return pedir<RespuestaBalanceo>('/estequiometria/balancear', { method: 'POST', body: JSON.stringify({ reactivos, productos }) });
}

export interface PedidoConversion {
  compuestoId: string;
  cantidad: number;
  unidad: UnidadCantidad;
  aUnidad: UnidadCantidad;
  pureza: number;
  concentracion: Concentracion | null;
  densidad: number | null;
}

export function convertirUnidades(p: PedidoConversion): Promise<RespuestaConversion> {
  return pedir<RespuestaConversion>('/unidades/convertir', {
    method: 'POST',
    body: JSON.stringify({
      compuesto_id: p.compuestoId,
      cantidad: p.cantidad,
      unidad: p.unidad,
      a_unidad: p.aUnidad,
      pureza: p.pureza,
      concentracion: p.concentracion,
      densidad_g_ml: p.densidad,
    }),
  });
}

export function convertirConcentracion(
  concentracion: Concentracion,
  ref: { compuestoId?: string; formula?: string },
  densidad: number | null,
): Promise<RespuestaConcentracion> {
  return pedir<RespuestaConcentracion>('/soluciones/convertir', {
    method: 'POST',
    body: JSON.stringify({
      concentracion,
      compuesto_id: ref.compuestoId ?? null,
      formula: ref.formula ?? null,
      densidad_g_ml: densidad,
    }),
  });
}

// ---------- Sistema, sesión y usuarios ----------
export const obtenerSistema = () => pedir<Sistema>('/sistema');

export async function iniciarSesion(email: string, clave: string): Promise<Usuario> {
  const r = await pedir<{ token: string; usuario: Usuario }>('/auth/login', { method: 'POST', body: JSON.stringify({ email, clave }) });
  guardarToken(r.token);
  return r.usuario;
}

export const obtenerYo = () => pedir<Usuario>('/auth/yo');
export const listarUsuarios = () => pedir<Usuario[]>('/usuarios');
export const crearUsuario = (u: { email: string; nombre: string; rol: Rol; clave: string }) =>
  pedir<Usuario>('/usuarios', { method: 'POST', body: JSON.stringify(u) });
export const cambiarUsuario = (id: number, c: { nombre?: string; rol?: Rol; activo?: boolean; clave?: string }) =>
  pedir<Usuario>(`/usuarios/${id}`, { method: 'PATCH', body: JSON.stringify(c) });

// ---------- Ensayos en el servidor ----------
export interface DatosGuardado {
  lote: string;
  notas: string;
  /** Si se informa, el ensayo nuevo reemplaza a ese (los ensayos no se editan: se corrigen con otro). */
  corrigeA: number | null;
}

export function guardarEnsayo(pedido: PedidoSimulacion, datos: DatosGuardado): Promise<EnsayoServidor> {
  const cuerpo = { ...cuerpoSimulacion(pedido), lote: datos.lote.trim() || null, notas: datos.notas };
  const ruta = datos.corrigeA ? `/ensayos/${datos.corrigeA}/corregir` : '/ensayos';
  return pedir<EnsayoServidor>(ruta, { method: 'POST', body: JSON.stringify(cuerpo) });
}

export interface FiltrosListado {
  lote?: string;
  estado?: EstadoEnsayo | '';
  soloVigentes?: boolean;
  /** "antiguos" pone primero lo que más tiempo lleva esperando (orden de una cola de revisión). Por defecto, los más nuevos primero. */
  orden?: 'recientes' | 'antiguos';
  limit: number;
  offset: number;
}

export async function listarEnsayos(f: FiltrosListado): Promise<{ ensayos: EnsayoResumen[]; total: number }> {
  const q = new URLSearchParams({ limit: String(f.limit), offset: String(f.offset) });
  if (f.lote?.trim()) q.set('lote', f.lote.trim());
  if (f.estado) q.set('estado', f.estado);
  if (f.soloVigentes) q.set('solo_vigentes', 'true');
  if (f.orden) q.set('orden', f.orden);
  const { datos, cabeceras: h } = await pedirConCabeceras<EnsayoResumen[]>(`/ensayos?${q}`);
  return { ensayos: datos, total: Number(h.get('X-Total-Count') ?? datos.length) };
}

export const obtenerConteoEnsayos = () => pedir<ConteoEstados>('/ensayos/conteo');
export const obtenerEnsayo = (id: number) => pedir<EnsayoServidor>(`/ensayos/${id}`);
export const agregarEvento = (id: number, tipo: TipoEvento, comentario: string) =>
  pedir<EnsayoServidor>(`/ensayos/${id}/eventos`, { method: 'POST', body: JSON.stringify({ tipo, comentario }) });
export const compararEnsayos = (ids: number[]) => pedir<ComparacionEnsayos>(`/ensayos/comparar?ids=${ids.join(',')}`);

/** Descarga un archivo del servidor (lleva la sesión, por eso no alcanza con un enlace). */
export async function descargar(ruta: string, nombreSugerido: string): Promise<void> {
  const r = await fetch(`${BASE}${ruta}`, { headers: cabeceras() });
  if (!r.ok) throw new Error(await textoDeError(r));
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement('a');
  a.href = url;
  a.download = nombreSugerido;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

// ---------- Auditoría ----------
export async function listarAuditoria(limit: number, offset: number): Promise<{ registros: RegistroAuditoria[]; total: number }> {
  const { datos, cabeceras: h } = await pedirConCabeceras<RegistroAuditoria[]>(`/auditoria?limit=${limit}&offset=${offset}`);
  return { registros: datos, total: Number(h.get('X-Total-Count') ?? datos.length) };
}
export const verificarAuditoria = () => pedir<VerificacionAuditoria>('/auditoria/verificar');
