import { useCallback, useEffect, useRef, useState } from 'react';
import { guardarEnsayo, obtenerCompuestos, obtenerConteoEnsayos, obtenerEspecificaciones, obtenerReacciones } from './api/client';
import { AuditoriaVista } from './components/Auditoria/AuditoriaVista';
import { BibliotecaVista } from './components/Biblioteca/BibliotecaVista';
import { CalculadorasVista } from './components/Calculadoras/CalculadorasVista';
import { Catalogo } from './components/Compuestos/Catalogo';
import type { CambiosComponente } from './components/Controles/ControlCompuesto';
import { AceptacionEnsayos } from './components/Ensayos/AceptacionEnsayos';
import { DialogoGuardar } from './components/Ensayos/DialogoGuardar';
import { EnsayosVista } from './components/Ensayos/EnsayosVista';
import { Cabecera, type Seccion } from './components/Layout/Cabecera';
import { Reactor } from './components/Reactor/Reactor';
import { Login } from './components/Sesion/Login';
import { UsuariosVista } from './components/Usuarios/UsuariosVista';
import { minimoDePureza, Resultados } from './components/Resultados/Resultados';
import { TablaPeriodica } from './components/Tabla/TablaPeriodica';
import { useSesion } from './hooks/useSesion';
import { useSimulacion } from './hooks/useSimulacion';
import {
  alcanzaRol,
  INCERTIDUMBRE_INICIAL,
  SIN_MEDIDOS,
  type ComponenteEnReactor,
  type Compuesto,
  type EnsayoServidor,
  type Medidos,
  type OpcionesIncertidumbre,
  type Reaccion,
  type Usuario,
} from './types';

// Misma mezcla del botón "Cargar ejemplo" de los prototipos: puntaje esperado = 85.
const EJEMPLO: Array<[string, number, number]> = [
  ['ibb', 134, 99],
  ['aa', 102, 98],
  ['cat', 20, 97],
  ['h2', 2, 99],
  ['co', 28, 98],
  ['exc', 30, 99],
];

const REACCION_INICIAL = 'ibuprofeno-simplificada';

/** Mezcla de ejemplo de una reacción: 1 mol de cada reactivo (en la proporción de la ecuación) y un poco de catalizador. */
function ejemploDe(r: Reaccion, catalogo: Compuesto[]): Array<[string, number, number]> {
  if (r.id === REACCION_INICIAL) return EJEMPLO;
  const pm = (id: string) => catalogo.find((c) => c.id === id)?.pm ?? 0;
  const lista: Array<[string, number, number]> = r.reactivos.map((x) => [x.id, Math.min(400, Math.max(1, Math.round(x.coef * pm(x.id)))), 98]);
  if (r.catalizador) lista.push([r.catalizador, 5, 98]);
  return lista;
}

export default function App() {
  const sesion = useSesion();
  if (!sesion.listo) return <div className="login"><p className="nota">Conectando…</p></div>;
  if (sesion.error) return <div className="login"><div className="alerta bad" role="alert">{sesion.error}. ¿Está corriendo el backend (puerto 8000)?</div></div>;
  if (sesion.sistema?.auth_activa && !sesion.usuario) return <Login onEntrar={sesion.entrar} />;
  if (!sesion.usuario) return <div className="login"><div className="alerta bad" role="alert">No se pudo identificar al usuario.</div></div>;
  return <Aplicacion sesion={sesion} usuario={sesion.usuario} />;
}

function Aplicacion({ sesion, usuario }: { sesion: ReturnType<typeof useSesion>; usuario: Usuario }) {
  const [seccion, setSeccion] = useState<Seccion>('reactor');
  const [catalogo, setCatalogo] = useState<Compuesto[]>([]);
  const [minimoPureza, setMinimoPureza] = useState<number | null>(null);
  const [errorCatalogo, setErrorCatalogo] = useState<string | null>(null);
  const [componentes, setComponentes] = useState<ComponenteEnReactor[]>([]);
  const [reacciones, setReacciones] = useState<Reaccion[]>([]);
  const [reaccionId, setReaccionId] = useState(REACCION_INICIAL);
  const [medidos, setMedidos] = useState<Medidos>(SIN_MEDIDOS);
  const [incert, setIncert] = useState<OpcionesIncertidumbre>(INCERTIDUMBRE_INICIAL);
  const [guardadoReciente, setGuardadoReciente] = useState(false);
  const [dialogoGuardar, setDialogoGuardar] = useState(false);
  const [corrigiendo, setCorrigiendo] = useState<number | null>(null);
  const [versionEnsayos, setVersionEnsayos] = useState(0);
  const [pendientes, setPendientes] = useState<number | undefined>(undefined);
  const siguienteUid = useRef(1);
  const esCalidad = alcanzaRol(usuario.rol, 'calidad');

  /** Ensayos esperando revisión o aprobación (globo de la pestaña Aceptación). Solo lo ve calidad. */
  const refrescarPendientes = useCallback(() => {
    if (!esCalidad) return;
    obtenerConteoEnsayos()
      .then((c) => setPendientes(c.registrado + c.revisado))
      .catch(() => setPendientes(undefined));
  }, [esCalidad]);

  useEffect(() => {
    refrescarPendientes();
  }, [refrescarPendientes, versionEnsayos]);

  useEffect(() => {
    obtenerCompuestos()
      .then(setCatalogo)
      .catch((e: unknown) => setErrorCatalogo(e instanceof Error ? e.message : 'Error desconocido'));
    obtenerReacciones()
      .then(setReacciones)
      .catch(() => setReacciones([]));
    obtenerEspecificaciones()
      .then((esp) => setMinimoPureza(minimoDePureza(esp)))
      .catch(() => setMinimoPureza(null));
  }, []);

  const { salida, error, cargando } = useSimulacion(componentes, reaccionId, medidos, incert);
  const reaccion = reacciones.find((r) => r.id === reaccionId) ?? null;
  const idProducto = reaccion?.productos.find((p) => p.principal)?.id;
  const producto = catalogo.find((c) => c.id === idProducto)?.nombre ?? 'Ibuprofeno';

  const cambiarReaccion = (id: string) => {
    setReaccionId(id);
    setComponentes([]);
    setMedidos(SIN_MEDIDOS);
  };
  const resultado = salida?.resultado ?? null;

  const nuevo = useCallback(
    (id: string, cantidad = 100, pureza = 98): ComponenteEnReactor => ({
      uid: siguienteUid.current++, id, cantidad, unidad: 'g', pureza, concentracion: null, densidad: null,
    }),
    [],
  );

  const agregar = useCallback(
    (id: string) => {
      if (!catalogo.some((c) => c.id === id)) return;
      setComponentes((prev) => (prev.some((x) => x.id === id) ? prev : [...prev, nuevo(id)]));
    },
    [catalogo, nuevo],
  );

  const cambiar = useCallback(
    (uid: number, cambios: CambiosComponente) =>
      setComponentes((prev) => prev.map((x) => (x.uid === uid ? { ...x, ...cambios } : x))),
    [],
  );

  const quitar = useCallback(
    (uid: number) => setComponentes((prev) => prev.filter((x) => x.uid !== uid)),
    [],
  );

  const cargarEjemplo = () =>
    setComponentes((reaccion ? ejemploDe(reaccion, catalogo) : EJEMPLO).map(([id, cantidad, pureza]) => nuevo(id, cantidad, pureza)));

  const confirmarGuardado = async (lote: string, notas: string) => {
    await guardarEnsayo(
      { componentes, reaccionId, medidos, incertidumbre: incert },
      { lote, notas, corrigeA: corrigiendo },
    );
    setDialogoGuardar(false);
    setCorrigiendo(null);
    setVersionEnsayos((v) => v + 1);
    setGuardadoReciente(true);
    setTimeout(() => setGuardadoReciente(false), 1800);
  };

  /** Carga la mezcla de un ensayo del servidor en el reactor (los datos medidos también). */
  const cargarEnsayo = (e: EnsayoServidor) => {
    const x = e.entrada;
    setReaccionId(x.reaccion_id);
    const rend = x.rendimiento_replicas_pct ?? (x.rendimiento_real_pct !== null ? [x.rendimiento_real_pct] : []);
    setMedidos({ rendimiento: rend.join(', '), pureza: x.pureza_real_pct, mediciones: x.mediciones });
    setComponentes(
      x.componentes.map((c) => ({
        uid: siguienteUid.current++,
        id: c.id,
        cantidad: c.gramos ?? c.cantidad ?? 0,
        unidad: c.gramos !== null ? 'g' : c.unidad,
        pureza: c.pureza,
        concentracion: c.concentracion,
        densidad: c.densidad_g_ml,
      })),
    );
    setCorrigiendo(null);
    setSeccion('reactor');
  };

  const corregirEnsayo = (e: EnsayoServidor) => {
    cargarEnsayo(e);
    setCorrigiendo(e.id);
  };

  return (
    <div className="app">
      <Cabecera
        seccion={seccion}
        onSeccion={setSeccion}
        corrigiendo={corrigiendo}
        producto={producto}
        usuario={usuario}
        onSalir={sesion.sistema?.auth_activa ? sesion.salir : null}
        onGuardar={() => setDialogoGuardar(true)}
        puedeGuardar={componentes.length > 0}
        avisoGuardado={guardadoReciente}
        pendientes={pendientes}
      />

      {errorCatalogo && (
        <div className="alerta bad aviso-global">
          No se pudo cargar la biblioteca: {errorCatalogo}. ¿Está corriendo el backend (puerto 8000)?
        </div>
      )}

      <main>
        {seccion === 'reactor' && (
          <div className="vista-reactor">
            <Catalogo
              compuestos={catalogo}
              usados={componentes.map((x) => x.id)}
              onAgregar={agregar}
              onAbrirBiblioteca={() => setSeccion('biblioteca')}
            />
            <Reactor
              numero={corrigiendo}
              componentes={componentes}
              catalogo={catalogo}
              resultado={resultado}
              reacciones={reacciones}
              reaccion={reaccion}
              onReaccion={cambiarReaccion}
              onAgregar={agregar}
              onCambiar={cambiar}
              onQuitar={quitar}
              onEjemplo={cargarEjemplo}
              onVaciar={() => setComponentes([])}
            />
            <Resultados
              resultado={resultado}
              alertas={salida?.alertas ?? []}
              cargando={cargando}
              error={error}
              minimoPureza={minimoPureza}
              producto={producto}
              medidos={medidos}
              onMedidos={setMedidos}
              incert={incert}
              onIncert={setIncert}
            />
          </div>
        )}

        {seccion === 'biblioteca' && (
          <BibliotecaVista
            compuestos={catalogo}
            usados={componentes.map((x) => x.id)}
            onAgregar={agregar}
            onIrReactor={() => setSeccion('reactor')}
          />
        )}

        {seccion === 'tabla' && <TablaPeriodica />}

        {seccion === 'calculadoras' && <CalculadorasVista catalogo={catalogo} />}

        {seccion === 'ensayos' && (
          <EnsayosVista catalogo={catalogo} usuario={usuario} version={versionEnsayos} onCargar={cargarEnsayo} onCorregir={corregirEnsayo} />
        )}

        {seccion === 'aceptacion' && (
          <AceptacionEnsayos catalogo={catalogo} usuario={usuario} version={versionEnsayos} onCambio={refrescarPendientes} />
        )}

        {seccion === 'auditoria' && <AuditoriaVista />}

        {seccion === 'usuarios' && <UsuariosVista yo={usuario} />}
      </main>

      {dialogoGuardar && (
        <DialogoGuardar corrigeA={corrigiendo} onGuardar={confirmarGuardado} onCancelar={() => setDialogoGuardar(false)} />
      )}

      <footer>
        Herramienta de estimación con datos simplificados; no reemplaza ensayos de laboratorio. El puntaje mide la
        calidad de la mezcla (pureza, rendimiento, balance estequiométrico), no la eficacia clínica. Los valores
        deben validarse con fuentes oficiales (USP, Ph. Eur.) y un profesional del área.
      </footer>
    </div>
  );
}
