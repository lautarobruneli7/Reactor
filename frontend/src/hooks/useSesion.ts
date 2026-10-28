import { useCallback, useEffect, useState } from 'react';
import { alVencerSesion, guardarToken, iniciarSesion, leerToken, obtenerSistema, obtenerYo } from '../api/client';
import type { Sistema, Usuario } from '../types';

/**
 * Estado de la sesión. Sin login (modo local) el servidor trata todo como un usuario administrador local;
 * con login hay que ingresar y el token se guarda solo mientras dure la pestaña.
 */
export function useSesion() {
  const [sistema, setSistema] = useState<Sistema | null>(null);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [listo, setListo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    obtenerSistema()
      .then(async (s) => {
        if (!vivo) return;
        setSistema(s);
        if (!s.auth_activa || leerToken()) {
          try {
            const u = await obtenerYo();
            if (vivo) setUsuario(u);
          } catch {
            guardarToken(null);
          }
        }
      })
      .catch((e: unknown) => vivo && setError(e instanceof Error ? e.message : 'No se pudo conectar con el servidor'))
      .finally(() => vivo && setListo(true));
    return () => {
      vivo = false;
    };
  }, []);

  useEffect(() => alVencerSesion(() => setUsuario(null)), []);

  const entrar = useCallback(async (email: string, clave: string) => {
    setUsuario(await iniciarSesion(email, clave));
  }, []);

  const salir = useCallback(() => {
    guardarToken(null);
    setUsuario(null);
  }, []);

  return { sistema, usuario, listo, error, entrar, salir };
}
