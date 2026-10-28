import { useEffect, useState } from 'react';
import { listarAuditoria, verificarAuditoria } from '../../api/client';
import type { RegistroAuditoria, VerificacionAuditoria } from '../../types';

const POR_PAGINA = 50;
const ACCIONES: Record<string, string> = {
  'ensayo.crear': 'Guardó un ensayo',
  'ensayo.comentario': 'Comentó un ensayo',
  'ensayo.revisado': 'Revisó un ensayo',
  'ensayo.aprobado': 'Aprobó un ensayo',
  'ensayo.rechazado': 'Rechazó un ensayo',
  'usuario.crear': 'Creó un usuario',
  'usuario.modificar': 'Modificó un usuario',
  'sesion.inicio': 'Inició sesión',
  'sesion.fallida': 'Intento de ingreso fallido',
};

/** Registro de todo lo hecho en el sistema y verificación de que nada fue alterado por fuera. */
export function AuditoriaVista() {
  const [registros, setRegistros] = useState<RegistroAuditoria[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [verif, setVerif] = useState<VerificacionAuditoria | null>(null);
  const [verificando, setVerificando] = useState(false);

  useEffect(() => {
    listarAuditoria(POR_PAGINA, pagina * POR_PAGINA)
      .then((r) => { setRegistros(r.registros); setTotal(r.total); setError(null); })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Error desconocido'));
  }, [pagina]);

  const verificar = () => {
    setVerificando(true);
    verificarAuditoria()
      .then((v) => { setVerif(v); setError(null); })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Error desconocido'))
      .finally(() => setVerificando(false));
  };

  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));
  return (
    <section className="panel">
      <div className="panel-cabecera">
        <h2 className="titulo-panel grande">Auditoría</h2>
        <button className="btn btn-primario" onClick={verificar} disabled={verificando}>{verificando ? 'Verificando…' : 'Verificar integridad'}</button>
      </div>
      <p className="nota">
        Cada acción queda en un registro encadenado por hashes: si alguien modifica o borra algo directamente en la base, la verificación lo detecta.
        Es evidencia de alteración, no una barrera contra quien administra la base: guardá el último hash en otro lugar.
      </p>
      {verif && (
        <div className={`alerta ${verif.ok ? 'ok' : 'bad'}`} role="status">
          {verif.ok
            ? `Integridad correcta: ${verif.registros} registros, ${verif.ensayos_verificados} ensayos y ${verif.eventos_verificados} eventos coinciden con su huella.`
            : `SE DETECTARON ALTERACIONES (${verif.total_errores}):`}
          {!verif.ok && <ul>{verif.errores.map((e, i) => <li key={i}>{e.registro_id ? `Registro ${e.registro_id}: ` : ''}{e.motivo}</li>)}</ul>}
          <div className="nota">Último hash: <span className="mono corto">{verif.ultimo_hash}</span></div>
        </div>
      )}
      {error && <div className="alerta bad" role="alert">{error}</div>}
      <div className="tabla-ancha">
        <table className="tabla-spec">
          <thead><tr><th>N°</th><th>Fecha</th><th>Persona</th><th>Acción</th><th>Referencia</th></tr></thead>
          <tbody>
            {registros.map((r) => (
              <tr key={r.id}>
                <td className="mono">{r.id}</td>
                <td>{new Date(r.creado_en).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'medium' })}</td>
                <td>{r.usuario ?? '—'}</td>
                <td>{ACCIONES[r.accion] ?? r.accion}</td>
                <td className="mono">{r.entidad}{r.entidad_id ? ` ${r.entidad_id}` : ''}{typeof r.detalle.email === 'string' ? ` · ${r.detalle.email}` : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {paginas > 1 && (
        <div className="paginacion">
          <button className="btn btn-contorno" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>← Más nuevos</button>
          <span className="nota">Página {pagina + 1} de {paginas}</span>
          <button className="btn btn-contorno" disabled={pagina + 1 >= paginas} onClick={() => setPagina((p) => p + 1)}>Más viejos →</button>
        </div>
      )}
    </section>
  );
}
