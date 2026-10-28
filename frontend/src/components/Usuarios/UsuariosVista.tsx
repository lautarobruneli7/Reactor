import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { cambiarUsuario, crearUsuario, listarUsuarios } from '../../api/client';
import type { Rol, Usuario } from '../../types';

const ROLES: Array<[Rol, string]> = [
  ['lectura', 'Lectura (solo ve)'],
  ['analista', 'Analista (guarda ensayos)'],
  ['calidad', 'Calidad (revisa y aprueba)'],
  ['admin', 'Administrador'],
];
const limpio = (e: unknown) => (e instanceof Error ? e.message.replace(/^Error \d+: /, '') : 'Error desconocido');

/** Administración mínima de usuarios (solo administradores). */
export function UsuariosVista({ yo }: { yo: Usuario }) {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [nuevo, setNuevo] = useState({ email: '', nombre: '', rol: 'analista' as Rol, clave: '' });

  const cargar = useCallback(() => {
    listarUsuarios().then(setUsuarios).catch((e: unknown) => setError(limpio(e)));
  }, []);
  useEffect(cargar, [cargar]);

  const crear = async (ev: FormEvent) => {
    ev.preventDefault();
    try {
      await crearUsuario(nuevo);
      setNuevo({ email: '', nombre: '', rol: 'analista', clave: '' });
      setError(null);
      setAviso('Usuario creado.');
      cargar();
    } catch (e) {
      setError(limpio(e));
    }
  };

  const cambiar = async (id: number, c: Parameters<typeof cambiarUsuario>[1], texto: string) => {
    try {
      await cambiarUsuario(id, c);
      setError(null);
      setAviso(texto);
      cargar();
    } catch (e) {
      setError(limpio(e));
    }
  };

  const restablecer = (u: Usuario) => {
    const clave = window.prompt(`Nueva clave para ${u.email} (10+ caracteres, con mayúsculas, minúsculas y un número):`);
    if (clave) void cambiar(u.id, { clave }, 'Clave restablecida.');
  };

  return (
    <section className="panel">
      <div className="panel-cabecera"><h2 className="titulo-panel grande">Usuarios</h2></div>
      {error && <div className="alerta bad" role="alert">{error}</div>}
      {aviso && <div className="alerta ok" role="status">{aviso}</div>}
      <div className="tabla-ancha">
        <table className="tabla-spec">
          <thead><tr><th>Correo</th><th>Nombre</th><th>Rol</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id}>
                <td>{u.email}{u.id === yo.id && <span className="nota"> (vos)</span>}</td>
                <td>{u.nombre}</td>
                <td>
                  <select className="campo" aria-label={`Rol de ${u.email}`} value={u.rol} onChange={(e) => cambiar(u.id, { rol: e.target.value as Rol }, 'Rol actualizado.')}>
                    {ROLES.map(([r, n]) => <option key={r} value={r}>{n}</option>)}
                  </select>
                </td>
                <td>{u.activo ? 'Activo' : 'Desactivado'}</td>
                <td className="acciones">
                  <button className="btn btn-contorno" onClick={() => cambiar(u.id, { activo: !u.activo }, u.activo ? 'Usuario desactivado.' : 'Usuario activado.')}>{u.activo ? 'Desactivar' : 'Activar'}</button>
                  <button className="btn btn-contorno" onClick={() => restablecer(u)}>Restablecer clave</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 className="subtitulo">Nuevo usuario</h3>
      <form className="form-usuario" onSubmit={crear}>
        <input className="campo" type="email" placeholder="correo" aria-label="Correo" required value={nuevo.email} onChange={(e) => setNuevo({ ...nuevo, email: e.target.value })} />
        <input className="campo" placeholder="nombre" aria-label="Nombre" required value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} />
        <select className="campo" aria-label="Rol" value={nuevo.rol} onChange={(e) => setNuevo({ ...nuevo, rol: e.target.value as Rol })}>
          {ROLES.map(([r, n]) => <option key={r} value={r}>{n}</option>)}
        </select>
        <input className="campo" type="password" placeholder="clave inicial" aria-label="Clave inicial" autoComplete="new-password" required value={nuevo.clave} onChange={(e) => setNuevo({ ...nuevo, clave: e.target.value })} />
        <button className="btn btn-primario">Crear</button>
      </form>
      <p className="nota">La clave tiene que tener 10 caracteres o más, con mayúsculas, minúsculas y al menos un número. Después de 5 intentos fallidos se bloquea el ingreso por 5 minutos.</p>
    </section>
  );
}
