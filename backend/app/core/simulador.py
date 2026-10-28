"""Orquestador: junta estequiometría, pureza, formulación y calidad.

Es una función pura (sin base de datos ni HTTP): recibe la mezcla, el catálogo
y la reacción elegida, y devuelve el resultado. Funciona con cualquier reacción
del catálogo (cualquier cantidad de reactivos y productos), no solo con la del
ibuprofeno. Así se puede testear y reemplazar el modelo sin tocar la API.
"""
import json
from functools import lru_cache
from pathlib import Path

from app.core import calidad, especificaciones as espec, estequiometria as est, formulacion, pureza, unidades
from app.core.balanceo import ecuacion_texto
from app.models.schemas import (
    Alerta,
    CargaResuelta,
    ComponenteEntrada,
    Compuesto,
    Especificacion,
    ProductoResultado,
    Reaccion,
    ReactivoResultado,
    Resultado,
    SimulacionSalida,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REACCION_POR_DEFECTO = "ibuprofeno-simplificada"


class ComponenteDesconocido(ValueError):
    pass


@lru_cache(maxsize=1)
def cargar_reacciones() -> dict[str, Reaccion]:
    with open(DATA_DIR / "reacciones.json", encoding="utf-8") as f:
        return {r["id"]: Reaccion.model_validate(r) for r in json.load(f)}


def cargar_reaccion(id_: str = REACCION_POR_DEFECTO) -> Reaccion:
    try:
        return cargar_reacciones()[id_]
    except KeyError:
        raise ComponenteDesconocido(f"Reacción desconocida: {id_}") from None


def _lista_natural(nombres: list[str]) -> str:
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def simular(
    entrada: list[ComponenteEntrada],
    catalogo: dict[str, Compuesto],
    reaccion: Reaccion,
    rendimiento_real_pct: float | None = None,
    *,
    pureza_real_pct: float | None = None,
    especificaciones: list[Especificacion] | None = None,
    mediciones: dict[str, float] | None = None,
) -> SimulacionSalida:
    p = reaccion.parametros
    alertas: list[Alerta] = []

    # --- Resolver componentes contra el catálogo
    vistos: set[str] = set()
    mezcla: dict[str, tuple[ComponenteEntrada, Compuesto]] = {}
    for e in entrada:
        if e.id not in catalogo:
            raise ComponenteDesconocido(f"Compuesto desconocido: {e.id}")
        if e.id in vistos:
            raise ValueError(f"Compuesto repetido: {e.id}")
        vistos.add(e.id)
        mezcla[e.id] = (e, catalogo[e.id])

    # Cantidad en gramos de material y fracción de soluto (solo para los que participan)
    cantidades: dict[str, tuple[float, float]] = {}

    def _cantidad(id_: str) -> tuple[float, float]:
        if id_ not in cantidades:
            e_, c_ = mezcla[id_]
            cantidades[id_] = unidades.resolver(e_, c_)
        return cantidades[id_]

    ids_reactivos = [r.id for r in reaccion.reactivos]
    participan = set(ids_reactivos) | {x for x in (reaccion.catalizador, reaccion.excipiente) if x}
    for id_, (_, c) in mezcla.items():
        if id_ not in participan:
            alertas.append(Alerta(tipo="warn", mensaje=f"{c.nombre} no participa en «{reaccion.nombre}»: se ignora."))

    # --- ¿Están todos los reactivos?
    faltan = [i for i in ids_reactivos if i not in mezcla]
    if faltan:
        nombres = [catalogo[i].nombre.lower() for i in ids_reactivos if i in catalogo]
        alertas.append(Alerta(
            tipo="warn",
            mensaje=f"Agregá los {len(ids_reactivos)} reactivos ({_lista_natural(nombres)}) para simular la reacción.",
        ))
        return SimulacionSalida(resultado=None, alertas=alertas)

    reactivos = []
    for part in reaccion.reactivos:
        e, c = mezcla[part.id]
        if not c.pm_aplicable or c.pm <= 0:
            raise ValueError(f"{c.nombre} no tiene peso molecular definido: no puede ser reactivo")
        gramos, fraccion = _cantidad(part.id)
        reactivos.append(est.Reactivo(c.id, c.nombre, gramos, e.pureza, c.pm, part.coef, fraccion))
        if fraccion < 1.0:
            alertas.append(Alerta(
                tipo="info",
                mensaje=(
                    f"{c.nombre} en solución: {fraccion * 100:.1f} % de la masa es {c.nombre.lower()}. "
                    "El solvente no se cuenta como impureza y el modelo no estima su efecto."
                ),
            ))

    limitante = est.reactivo_limitante(reactivos)
    moles_teoricos = limitante.moles_equivalentes
    if moles_teoricos <= 0:
        alertas.append(Alerta(
            tipo="bad",
            mensaje=f"{limitante.nombre} tiene cantidad efectiva cero: no se puede calcular el rendimiento.",
        ))
        return SimulacionSalida(resultado=None, alertas=alertas)

    principal = reaccion.principal
    c_principal = catalogo[principal.id]
    g_teorico = est.gramos_de_producto(moles_teoricos * principal.coef, c_principal.pm)

    # --- Catalizador
    f_cat = 1.0
    if reaccion.catalizador:
        if reaccion.catalizador in mezcla:
            e_cat, c_cat = mezcla[reaccion.catalizador]
            if p.catalizador_ratio_optimo is not None and c_cat.pm > 0:
                g_cat, frac_cat = _cantidad(reaccion.catalizador)
                mol_cat = est.moles_utiles(g_cat * frac_cat, e_cat.pureza, c_cat.pm)
                ratio = mol_cat / moles_teoricos
                f_cat = pureza.factor_catalizador(ratio, p)
                if ratio < p.catalizador_ratio_minimo:
                    alertas.append(Alerta(tipo="warn", mensaje="Poco catalizador: la reacción sería lenta o incompleta."))
                if ratio > p.catalizador_ratio_maximo:
                    alertas.append(Alerta(tipo="warn", mensaje="Exceso de catalizador: más residuos y costo, sin ganancia de rendimiento."))
        elif p.catalizador_requerido:
            f_cat = p.factor_catalizador_ausente
            alertas.append(Alerta(tipo="bad", mensaje="Sin catalizador el rendimiento cae fuertemente."))
        else:
            nombre_cat = catalogo[reaccion.catalizador].nombre.lower()
            alertas.append(Alerta(
                tipo="warn",
                mensaje=f"Sin {nombre_cat}: esta reacción suele hacerse con catalizador, pero el modelo no estima su efecto.",
            ))

    # --- Excesos de reactivos
    excesos = [(r.nombre, est.exceso_relativo(r, moles_teoricos)) for r in reactivos]
    nombre_peor, exceso_max = max(excesos, key=lambda x: x[1])
    if exceso_max > p.exceso_alerta:
        alertas.append(Alerta(
            tipo="warn",
            mensaje=f"Gran exceso de {nombre_peor} (+{exceso_max * 100:.0f}%): sobrante que hay que separar.",
        ))
    f_exc = pureza.factor_exceso(exceso_max, p)

    # --- Rendimiento y pureza
    if rendimiento_real_pct is not None:
        rendimiento = rendimiento_real_pct / 100.0
        origen_rend = "experimental"
        alertas.append(Alerta(tipo="ok", mensaje=f"Se usó el rendimiento experimental informado ({rendimiento_real_pct:g}%)."))
    else:
        rendimiento = min(p.rendimiento_maximo, p.rendimiento_base * f_cat * f_exc)
        origen_rend = "modelo"
    g_real = g_teorico * rendimiento
    if pureza_real_pct is not None:
        pureza_prod = pureza_real_pct
        origen_pureza = "experimental"
    else:
        pureza_prod = pureza.pureza_producto([r.pureza for r in reactivos], f_cat, p)
        origen_pureza = "modelo"

    # --- Formulación
    pct_activo: float | None = None
    if reaccion.excipiente:
        if reaccion.excipiente in mezcla:
            e_exc, _ = mezcla[reaccion.excipiente]
            g_exc, frac_exc = _cantidad(reaccion.excipiente)
            pct_activo = formulacion.pct_principio_activo(
                g_real, formulacion.gramos_efectivos(g_exc * frac_exc, e_exc.pureza)
            )
        else:
            alertas.append(Alerta(
                tipo="warn",
                mensaje="Sin excipiente: solo se evalúa el principio activo, no la formulación final.",
            ))

    # --- Calidad
    puntaje = calidad.puntaje_calidad(rendimiento, pureza_prod, exceso_max, p)
    _, _, s_balance = calidad.subpuntajes(rendimiento, pureza_prod, exceso_max, p)
    cumple = calidad.cumple_pureza(pureza_prod, p.pureza_especificada_minima)
    adjetivo = "medida" if origen_pureza == "experimental" else "estimada"
    if cumple:
        alertas.append(Alerta(
            tipo="ok",
            mensaje=f"Pureza {adjetivo} {pureza_prod:.1f}%: cumple el mínimo orientativo ({p.pureza_especificada_minima}%).",
        ))
    else:
        alertas.append(Alerta(
            tipo="bad",
            mensaje=f"Pureza {adjetivo} {pureza_prod:.1f}%: NO cumple el mínimo orientativo ({p.pureza_especificada_minima}%).",
        ))

    # --- Especificación de varios parámetros (el modelo solo estima la pureza; el resto, mediciones)
    evaluacion, cumplimiento, avisos = espec.evaluar(
        especificaciones or [], principal.id, pureza_prod, origen_pureza, mediciones or {}
    )
    for a in avisos:
        alertas.append(Alerta(tipo="warn", mensaje=a))
    if cumplimiento == "incompleto":
        pendientes = [x.parametro for x in evaluacion if x.estado in ("sin_dato", "sin_limite")]
        alertas.append(Alerta(
            tipo="info",
            mensaje="Especificación incompleta: faltan datos o límites en " + ", ".join(pendientes) + ". No se puede decir que el producto cumpla.",
        ))
    elif cumplimiento == "no_cumple":
        malos = [x.parametro for x in evaluacion if x.estado == "no_cumple"]
        alertas.append(Alerta(tipo="bad", mensaje="No cumple la especificación en: " + ", ".join(malos) + "."))

    # --- Detalle por reactivo y por producto
    det_reactivos = []
    for r in reactivos:
        g_utiles = r.moles_utiles * r.pm
        g_consumidos = moles_teoricos * r.coef * r.pm
        det_reactivos.append(ReactivoResultado(
            id=r.id,
            nombre=r.nombre,
            coef=r.coef,
            gramos_cargados=round(r.gramos, 3),
            moles_utiles=round(r.moles_utiles, 5),
            exceso_pct=round(est.exceso_relativo(r, moles_teoricos) * 100, 2),
            gramos_consumidos=round(g_consumidos, 3),
            gramos_sobrantes=round(max(0.0, g_utiles - g_consumidos), 3),
            limitante=r.id == limitante.id,
            fraccion_soluto=round(r.fraccion, 5),
        ))
    det_productos = []
    for prod in reaccion.productos:
        c = catalogo[prod.id]
        g_t = est.gramos_de_producto(moles_teoricos * prod.coef, c.pm)
        det_productos.append(ProductoResultado(
            id=c.id, nombre=c.nombre, coef=prod.coef, principal=prod.principal, pm=c.pm,
            gramos_teoricos=round(g_t, 3), gramos_estimados=round(g_t * rendimiento, 3),
        ))
    cargas = []
    for id_ in dict.fromkeys([*ids_reactivos, *[x for x in (reaccion.catalizador, reaccion.excipiente) if x]]):
        if id_ in mezcla:
            g_, f_ = _cantidad(id_)
            c_ = catalogo[id_]
            e_ = mezcla[id_][0]
            neto = g_ * f_ * e_.pureza / 100.0
            cargas.append(CargaResuelta(
                id=id_, gramos_material=round(g_, 4), fraccion_soluto=round(f_, 5),
                moles_netos=round(neto / c_.pm, 6) if c_.pm_aplicable and c_.pm > 0 else None,
            ))
    economia = est.economia_atomica(
        c_principal.pm, principal.coef, [(catalogo[r.id].pm, r.coef) for r in reaccion.reactivos]
    )
    ecuacion = ecuacion_texto(
        [(catalogo[r.id].formula or r.id, r.coef) for r in reaccion.reactivos],
        [(catalogo[x.id].formula or x.id, x.coef) for x in reaccion.productos],
    )

    if origen_rend == "experimental" and origen_pureza == "experimental":
        origen = "medido"
    elif origen_rend == "experimental" or origen_pureza == "experimental":
        origen = "mixto"
    else:
        origen = "estimacion"

    return SimulacionSalida(
        resultado=Resultado(
            puntaje=puntaje,
            categoria=calidad.categoria(puntaje),
            rendimiento_pct=round(rendimiento * 100, 2),
            pureza_producto_pct=round(pureza_prod, 2),
            balance_pct=round(min(100.0, s_balance), 2),
            reactivo_limitante=limitante.nombre,
            gramos_teoricos=round(g_teorico, 2),
            gramos_estimados=round(g_real, 2),
            pm_producto=c_principal.pm,
            pct_principio_activo=None if pct_activo is None else round(pct_activo, 2),
            cumple_pureza=cumple,
            reaccion_id=reaccion.id,
            reaccion_nombre=reaccion.nombre,
            ecuacion=ecuacion,
            economia_atomica_pct=round(economia, 2),
            moles_reaccion=round(moles_teoricos, 6),
            rendimiento_origen=origen_rend,
            pureza_origen=origen_pureza,
            origen=origen,
            estado_validacion=reaccion.estado_validacion,
            reactivos=det_reactivos,
            productos=det_productos,
            cargas=cargas,
            especificaciones=evaluacion,
            cumplimiento_especificaciones=cumplimiento,
        ),
        alertas=alertas,
    )
