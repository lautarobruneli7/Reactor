import { useState, type FormEvent } from 'react';

interface Props {
  onEntrar: (email: string, clave: string) => Promise<void>;
}

export function Login({ onEntrar }: Props) {
  const [email, setEmail] = useState('');
  const [clave, setClave] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const enviar = async (ev: FormEvent) => {
    ev.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await onEntrar(email, clave);
    } catch (e) {
      setError(e instanceof Error ? e.message.replace(/^Error \d+: /, '') : 'No se pudo iniciar sesión');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="login">
      <form className="panel login-caja" onSubmit={enviar} aria-label="Iniciar sesión">
        <h1 className="titulo-panel grande">Retorta</h1>
        <p className="nota">Ingresá con tu usuario para ver y guardar ensayos.</p>
        <label className="nota" htmlFor="login-email">Correo</label>
        <input id="login-email" className="campo" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label className="nota" htmlFor="login-clave">Clave</label>
        <input id="login-clave" className="campo" type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} required />
        {error && <div className="alerta bad" role="alert">{error}</div>}
        <button className="btn btn-primario ancho" disabled={enviando || !email || !clave}>{enviando ? 'Ingresando…' : 'Ingresar'}</button>
      </form>
    </div>
  );
}
