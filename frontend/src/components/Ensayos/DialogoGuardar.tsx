import { useState, type FormEvent } from 'react';

interface Props {
  corrigeA: number | null;
  onGuardar: (lote: string, notas: string) => Promise<void>;
  onCancelar: () => void;
}

/** Pide lote y notas antes de guardar. El resultado no se envía: lo calcula el servidor con la mezcla. */
export function DialogoGuardar({ corrigeA, onGuardar, onCancelar }: Props) {
  const [lote, setLote] = useState('');
  const [notas, setNotas] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const enviar = async (ev: FormEvent) => {
    ev.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await onGuardar(lote, notas);
    } catch (e) {
      setError(e instanceof Error ? e.message.replace(/^Error \d+: /, '') : 'No se pudo guardar');
      setGuardando(false);
    }
  };

  return (
    <div className="modal-fondo" role="dialog" aria-modal="true" aria-label="Guardar ensayo">
      <form className="panel modal" onSubmit={enviar}>
        <h2 className="titulo-panel grande">{corrigeA ? `Guardar corrección del N° ${String(corrigeA).padStart(3, '0')}` : 'Guardar ensayo'}</h2>
        {corrigeA && (
          <p className="nota">
            Los ensayos no se editan: se guarda uno nuevo que reemplaza al N° {String(corrigeA).padStart(3, '0')}. El original queda
            tal cual, marcado como reemplazado. Explicá el motivo en las notas.
          </p>
        )}
        <label className="nota" htmlFor="g-lote">Lote (opcional)</label>
        <input id="g-lote" className="campo" value={lote} maxLength={100} onChange={(e) => setLote(e.target.value)} autoFocus />
        <label className="nota" htmlFor="g-notas">Notas {corrigeA ? '(motivo de la corrección)' : '(opcional)'}</label>
        <textarea id="g-notas" className="campo" rows={4} maxLength={4000} value={notas} onChange={(e) => setNotas(e.target.value)} />
        <p className="nota">El servidor vuelve a calcular el resultado con esta mezcla y lo guarda junto con la versión del modelo y una huella de trazabilidad.</p>
        {error && <div className="alerta bad" role="alert">{error}</div>}
        <div className="acciones">
          <button type="button" className="btn btn-contorno" onClick={onCancelar} disabled={guardando}>Cancelar</button>
          <button className="btn btn-primario" disabled={guardando || (!!corrigeA && !notas.trim())}>{guardando ? 'Guardando…' : 'Guardar'}</button>
        </div>
      </form>
    </div>
  );
}
