import { useEffect, useState } from 'react';

interface Props {
  value: number | null;
  /** Se llama con el número escrito, o con null si se vació el campo. */
  onValor: (v: number | null) => void;
  min?: number;
  max?: number;
  step?: number | 'any';
  className?: string;
  ariaLabel?: string;
  placeholder?: string;
  id?: string;
}

/**
 * Campo numérico que no pisa lo que se está escribiendo ("0." no se vuelve "0"):
 * guarda el texto y solo lo reemplaza cuando el valor de afuera cambia por otra causa.
 */
export function CampoNumero({ value, onValor, min, max, step = 'any', className = 'campo campo-num mono', ariaLabel, placeholder, id }: Props) {
  const [texto, setTexto] = useState(value === null ? '' : String(value));

  useEffect(() => {
    const escrito = texto === '' ? null : Number(texto);
    if (value !== escrito) setTexto(value === null ? '' : String(value));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <input
      id={id}
      className={className}
      type="number"
      inputMode="decimal"
      aria-label={ariaLabel}
      placeholder={placeholder}
      min={min}
      max={max}
      step={step}
      value={texto}
      onChange={(e) => {
        const t = e.target.value;
        setTexto(t);
        if (t === '') onValor(null);
        else if (Number.isFinite(Number(t))) onValor(Number(t));
      }}
    />
  );
}
