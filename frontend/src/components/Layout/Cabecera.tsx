import { alcanzaRol, type Usuario } from '../../types';

export type Seccion = 'reactor' | 'biblioteca' | 'tabla' | 'calculadoras' | 'ensayos' | 'aceptacion' | 'auditoria' | 'usuarios';

const SECCIONES: Array<[Seccion, string, 'lectura' | 'calidad' | 'admin']> = [
  ['reactor', 'Reactor', 'lectura'],
  ['biblioteca', 'Biblioteca', 'lectura'],
  ['tabla', 'Tabla periódica', 'lectura'],
  ['calculadoras', 'Calculadoras', 'lectura'],
  ['ensayos', 'Ensayos', 'lectura'],
  ['aceptacion', 'Aceptación', 'calidad'],
  ['auditoria', 'Auditoría', 'calidad'],
  ['usuarios', 'Usuarios', 'admin'],
];

interface Props {
  seccion: Seccion;
  onSeccion: (s: Seccion) => void;
  producto: string;
  onGuardar: () => void;
  puedeGuardar: boolean;
  avisoGuardado: boolean;
  usuario: Usuario | null;
  /** Solo con login: en modo local no hay sesión que cerrar. */
  onSalir: (() => void) | null;
  /** Número del ensayo que se está corrigiendo, si hay uno. */
  corrigiendo: number | null;
  /** Ensayos esperando revisión o aprobación; se muestra como globo en la pestaña Aceptación. */
  pendientes?: number;
}

export function Cabecera({ seccion, onSeccion, producto, onGuardar, puedeGuardar, avisoGuardado, usuario, onSalir, corrigiendo, pendientes }: Props) {
  return (
    <header className="cabecera">
      <div className="marca">
        <span className="marca-logo" aria-hidden>
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 3h6M10 3v6.5L5.4 18a2 2 0 0 0 1.8 3h9.6a2 2 0 0 0 1.8-3L14 9.5V3" />
            <path d="M7.5 15h9" />
          </svg>
        </span>
        <span className="marca-nombre">Retorta</span>
      </div>

      <nav className="pestanas" aria-label="Secciones">
        {SECCIONES.filter(([, , minimo]) => alcanzaRol(usuario?.rol, minimo)).map(([id, nombre]) => (
          <button
            key={id}
            className={`pestana${seccion === id ? ' activa' : ''}`}
            onClick={() => onSeccion(id)}
            aria-current={seccion === id ? 'page' : undefined}
          >
            {nombre}
            {id === 'aceptacion' && pendientes ? <span className="pestana-globo" aria-label={`${pendientes} pendientes`}>{pendientes}</span> : null}
          </button>
        ))}
      </nav>

      <div className="cabecera-der">
        <span className="chip-ensayo">
          <span className="mono">{corrigiendo ? `corrige N° ${String(corrigiendo).padStart(3, '0')}` : 'sin guardar'}</span> <strong>{producto}</strong>
        </span>
        <button
          className="btn btn-primario"
          onClick={onGuardar}
          disabled={!puedeGuardar || !alcanzaRol(usuario?.rol, 'analista')}
          title={alcanzaRol(usuario?.rol, 'analista') ? undefined : 'Tu rol es de solo lectura: no puede guardar ensayos'}
        >
          {avisoGuardado ? '✓ Guardado' : corrigiendo ? `Guardar corrección de N° ${String(corrigiendo).padStart(3, '0')}` : 'Guardar ensayo'}
        </button>
        {onSalir && usuario && (
          <span className="usuario-chip">
            <span title={usuario.email}>{usuario.nombre}</span> <span className="nota">({usuario.rol})</span>{' '}
            <button className="btn btn-contorno" onClick={onSalir}>Salir</button>
          </span>
        )}
      </div>
    </header>
  );
}
