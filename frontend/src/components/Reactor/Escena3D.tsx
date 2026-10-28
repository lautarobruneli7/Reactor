import { useEffect, useRef, useState } from 'react';
import { crearEscena, type EscenaApi, type EstadoEscena } from './motor3d';

interface Props {
  estado: EstadoEscena;
  /** Rotación automática de la cámara. */
  giro: boolean;
  /** Al cambiar este número, la cámara vuelve a la vista inicial. */
  vistaKey: number;
}

/** Dibuja el reactor en 3D. Toda la lógica de Three.js vive en motor3d.ts. */
export function Escena3D({ estado, giro, vistaKey }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const escena = useRef<EscenaApi | null>(null);
  const previos = useRef<Set<string>>(new Set());
  const [sinWebGL, setSinWebGL] = useState(false);

  useEffect(() => {
    escena.current = crearEscena(contenedor.current!);
    setSinWebGL(!escena.current);
    return () => {
      escena.current?.dispose();
      escena.current = null;
    };
  }, []);

  useEffect(() => {
    escena.current?.setAuto(giro);
  }, [giro]);

  useEffect(() => {
    if (vistaKey > 0) escena.current?.resetVista();
  }, [vistaKey]);

  useEffect(() => {
    const api = escena.current;
    if (!api) return;
    api.sync(estado);
    // Gotas solo para los compuestos que no estaban en la sincronización anterior.
    estado.items
      .filter((x) => !previos.current.has(x.id))
      .forEach((x, i) => setTimeout(() => escena.current?.verter(x), i * 260));
    previos.current = new Set(estado.items.map((x) => x.id));
  }, [estado]);

  return (
    <div className="escena3d" ref={contenedor}>
      {sinWebGL && <div className="sin-webgl">Tu navegador no tiene WebGL: no se puede mostrar el reactor 3D.</div>}
    </div>
  );
}
