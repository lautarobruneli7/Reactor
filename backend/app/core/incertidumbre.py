"""Incertidumbre de una simulación por Monte Carlo.

Qué hace: repite la simulación muchas veces perturbando las ENTRADAS (cada pesada y la pureza
de cada insumo) y, si se informa, el rendimiento y la pureza del producto. Devuelve la media, el
desvío y los percentiles 5, 50 y 95 de rendimiento, pureza, gramos y puntaje, y la probabilidad
de cumplir el mínimo de pureza.

Qué NO hace (y el resultado lo dice):
- No cuantifica el error del modelo. Con rendimiento «de modelo» y sin `sd_rendimiento_pts`, el
  intervalo cubre solo el efecto de pesar e informar purezas con error, no cuánto se aparta el
  modelo de la realidad (hoy sus parámetros no están validados).
- Los desvíos por defecto son supuestos, no datos. Hay que reemplazarlos por la incertidumbre de
  la balanza, los certificados de análisis y las réplicas del laboratorio.
"""
import math
import random
import statistics

from app.core import simulador, unidades
from app.models.schemas import (
    ComponenteEntrada,
    Compuesto,
    Especificacion,
    Incertidumbre,
    IntervaloMetrica,
    ParametrosIncertidumbre,
    Reaccion,
    SimulacionEntrada,
)


def rendimiento_medido(entrada: SimulacionEntrada) -> tuple[float | None, float | None]:
    """(rendimiento medido en %, desvío de las réplicas en puntos) a partir de lo que informó el usuario."""
    if entrada.rendimiento_replicas_pct:
        r = entrada.rendimiento_replicas_pct
        return statistics.fmean(r), statistics.stdev(r)
    return entrada.rendimiento_real_pct, None


def _cuantil(ordenados: list[float], q: float) -> float:
    pos = (len(ordenados) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return ordenados[lo]
    return ordenados[lo] + (ordenados[hi] - ordenados[lo]) * (pos - lo)


def _intervalo(valores: list[float], decimales: int = 2) -> IntervaloMetrica:
    s = sorted(valores)
    return IntervaloMetrica(
        media=round(statistics.fmean(s), decimales),
        sd=round(statistics.pstdev(s), decimales),
        p5=round(_cuantil(s, 0.05), decimales),
        p50=round(_cuantil(s, 0.50), decimales),
        p95=round(_cuantil(s, 0.95), decimales),
    )


def _acotar(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def analizar(
    entrada: SimulacionEntrada,
    catalogo: dict[str, Compuesto],
    reaccion: Reaccion,
    params: ParametrosIncertidumbre,
    especificaciones: list[Especificacion] | None = None,
) -> Incertidumbre | None:
    """Devuelve None si la mezcla no permite simular (faltan reactivos, cantidad cero...)."""
    rend_medido, sd_replicas = rendimiento_medido(entrada)
    base = simulador.simular(
        entrada.componentes, catalogo, reaccion, rend_medido,
        pureza_real_pct=entrada.pureza_real_pct, especificaciones=especificaciones, mediciones=entrada.mediciones,
    )
    if base.resultado is None:
        return None

    # Cantidades en gramos de material (una vez), para perturbar la pesada
    participan = {r.id for r in reaccion.reactivos} | {x for x in (reaccion.catalizador, reaccion.excipiente) if x}
    fijos: list[tuple[ComponenteEntrada, float]] = []
    for e in entrada.componentes:
        if e.id in participan:
            gramos, _ = unidades.resolver(e, catalogo[e.id])
            fijos.append((e, gramos))

    notas: list[str] = []
    sd_rend: float | None = sd_replicas
    if sd_rend is None:
        sd_rend = params.sd_rendimiento_pts
    if rend_medido is not None and sd_replicas is None and params.sd_rendimiento_pts is None:
        notas.append(
            "Rendimiento medido con una sola pesada de resultado: no hay variabilidad entre corridas. Informá réplicas (`rendimiento_replicas_pct`) o `sd_rendimiento_pts`."
        )
    incluye_modelo = sd_rend is not None and sd_rend > 0
    if rend_medido is None and not incluye_modelo:
        notas.append(
            "El rendimiento viene del modelo y no se informó `sd_rendimiento_pts`: el intervalo NO incluye cuánto se aparta el modelo de la realidad (sus parámetros no están validados)."
        )
    if sd_replicas is not None:
        notas.append(
            f"El desvío del rendimiento ({sd_replicas:.2f} puntos) es el de {len(entrada.rendimiento_replicas_pct or [])} réplicas: variabilidad entre corridas del laboratorio."
        )
    if entrada.pureza_real_pct is not None and not params.sd_pureza_producto_pts:
        notas.append("La pureza del producto es una medición puntual sin desvío informado (`sd_pureza_producto_pts`).")
    notas.append(
        "Los desvíos de pesada y de pureza son supuestos del analista salvo que se los reemplace por los de la balanza y los certificados de análisis."
    )

    rng = random.Random(params.semilla)
    rend, pur, gr, pun, cumple = [], [], [], [], []
    for _ in range(params.n):
        perturbados = []
        for e, gramos in fijos:
            g = max(0.0, gramos * (1.0 + rng.gauss(0.0, params.sd_masa_rel_pct / 100.0)))
            pz = _acotar(e.pureza + rng.gauss(0.0, params.sd_pureza_pts), 0.0, 100.0)
            perturbados.append(ComponenteEntrada(
                id=e.id, gramos=g, pureza=pz, concentracion=e.concentracion, densidad_g_ml=e.densidad_g_ml,
            ))

        # Rendimiento y pureza del producto de esta corrida
        r_ov: float | None = None
        p_ov: float | None = None
        necesita_modelo = (rend_medido is None and incluye_modelo) or (
            entrada.pureza_real_pct is None and bool(params.sd_pureza_producto_pts)
        )
        modelo = None
        if necesita_modelo:
            previo = simulador.simular(perturbados, catalogo, reaccion).resultado
            if previo is None:
                continue
            modelo = previo
        if rend_medido is not None:
            r_ov = _acotar(rng.gauss(rend_medido, sd_rend), 0.0, 100.0) if sd_rend else rend_medido
        elif incluye_modelo and modelo is not None:
            r_ov = _acotar(modelo.rendimiento_pct + rng.gauss(0.0, sd_rend), 0.0, 100.0)
        sd_p = params.sd_pureza_producto_pts or 0.0
        if entrada.pureza_real_pct is not None:
            p_ov = _acotar(rng.gauss(entrada.pureza_real_pct, sd_p), 0.0, 100.0) if sd_p else entrada.pureza_real_pct
        elif sd_p and modelo is not None:
            p_ov = _acotar(modelo.pureza_producto_pct + rng.gauss(0.0, sd_p), 0.0, 100.0)

        res = simulador.simular(perturbados, catalogo, reaccion, r_ov, pureza_real_pct=p_ov).resultado
        if res is None:
            continue
        rend.append(res.rendimiento_pct)
        pur.append(res.pureza_producto_pct)
        gr.append(res.gramos_estimados)
        pun.append(float(res.puntaje))
        cumple.append(1.0 if res.cumple_pureza else 0.0)

    if len(rend) < max(50, params.n // 10):
        return None

    return Incertidumbre(
        metodo="Monte Carlo (perturbación normal de las entradas)",
        n=params.n,
        corridas_validas=len(rend),
        semilla=params.semilla,
        supuestos={
            "sd_masa_rel_pct": params.sd_masa_rel_pct,
            "sd_pureza_pts": params.sd_pureza_pts,
            "sd_rendimiento_pts": sd_rend,
            "sd_pureza_producto_pts": params.sd_pureza_producto_pts,
        },
        incluye_incertidumbre_del_modelo=incluye_modelo,
        rendimiento_pct=_intervalo(rend),
        pureza_producto_pct=_intervalo(pur),
        gramos_estimados=_intervalo(gr),
        puntaje=_intervalo(pun, 1),
        prob_cumple_pureza=round(statistics.fmean(cumple), 4),
        notas=notas,
    )
