"""Unidades de cantidad y concentración: g, kg, mg, mL, L, mol, mmol, %p/p, %p/v y molaridad.

Reglas (todas explícitas, para poder auditarlas):

- **Pureza** y **concentración** son datos distintos. La pureza (%) dice cuánto del compuesto
  (o del soluto) es el compuesto buscado y cuánto es impureza. La concentración dice cuánto de la
  masa del material es el compuesto cuando viene en solución (HCl 37 % p/p = 0,37 g de HCl por
  gramo de solución; el resto es agua, que NO es una impureza).
- Moles (`mol`, `mmol`) son moles NETOS del compuesto: ya descontadas la pureza y la concentración.
  La masa de material que hay que pesar sale de dividir por ambas.
- Para pasar volumen a masa hace falta la densidad. Para líquidos puros se usa la del catálogo
  (`data/densidades.json`, con fuente y temperatura) o la que informe el usuario; para soluciones
  hay que informar la densidad de ESA solución: no se inventa.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models.schemas import ComponenteEntrada, Compuesto, Concentracion

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

MASA_G = {"g": 1.0, "kg": 1000.0, "mg": 0.001}
VOLUMEN_ML = {"mL": 1.0, "L": 1000.0}
MOLES = {"mol": 1.0, "mmol": 0.001}

_TOL = 1e-6


class FaltaDensidad(ValueError):
    """No hay densidad para convertir entre volumen y masa (o para interpretar la concentración)."""


@lru_cache(maxsize=1)
def densidades() -> dict[str, dict]:
    """Densidades de líquidos puros del catálogo (g/mL), con temperatura y fuente."""
    try:
        with open(DATA_DIR / "densidades.json", encoding="utf-8") as f:
            return json.load(f)["densidades"]
    except FileNotFoundError:
        return {}


def densidad_pura(compuesto_id: str) -> dict | None:
    return densidades().get(compuesto_id)


# ---------------------------------------------------------------------------
# Concentración
# ---------------------------------------------------------------------------
def fraccion_masica(conc: Concentracion | None, pm: float, densidad_solucion: float | None) -> float:
    """Fracción de la masa de la solución que es soluto (0 < w ≤ 1). Sin concentración, 1."""
    if conc is None:
        return 1.0
    if conc.tipo == "p/p":
        w = conc.valor / 100.0
    else:
        if densidad_solucion is None:
            raise FaltaDensidad(
                "Para interpretar una concentración %p/v o molar hace falta la densidad de la solución (g/mL): informala en `densidad_g_ml`"
            )
        if conc.tipo == "p/v":
            w = conc.valor / (100.0 * densidad_solucion)
        else:
            if pm <= 0:
                raise ValueError("El compuesto no tiene peso molecular: no se puede usar molaridad")
            w = conc.valor * pm / (1000.0 * densidad_solucion)
    if w <= 0 or w > 1.0 + _TOL:
        raise ValueError(
            f"La concentración indicada es imposible: equivale a {w * 100:.1f} % de soluto en masa (tiene que estar entre 0 y 100 %)"
        )
    return min(w, 1.0)


def convertir_concentracion(conc: Concentracion, pm: float, densidad_solucion: float | None) -> dict:
    """Expresa una concentración en las tres formas. Las que necesitan densidad salen None si falta."""
    w = fraccion_masica(conc, pm, densidad_solucion)
    out: dict = {"p_p_pct": w * 100.0, "p_v_pct": None, "molar": None, "g_por_l": None, "fraccion_masica": w}
    if densidad_solucion is not None:
        g_l = w * densidad_solucion * 1000.0
        out["g_por_l"] = g_l
        out["p_v_pct"] = g_l / 10.0
        out["molar"] = g_l / pm if pm > 0 else None
    out["densidad_g_ml"] = densidad_solucion
    return out


# ---------------------------------------------------------------------------
# Cantidad
# ---------------------------------------------------------------------------
def _densidad_de_carga(e: ComponenteEntrada, c: Compuesto) -> float:
    """Densidad (g/mL) del material tal como se carga, para pasar volumen a masa."""
    if e.densidad_g_ml is not None:
        return e.densidad_g_ml
    if e.concentracion is not None:
        raise FaltaDensidad(
            f"Para pasar mL de una solución de {c.nombre} a gramos hace falta la densidad de esa solución (g/mL): informala en `densidad_g_ml`"
        )
    d = densidad_pura(c.id)
    if d is None:
        raise FaltaDensidad(
            f"No hay densidad de {c.nombre} en el catálogo: informala en `densidad_g_ml` para convertir volumen a masa"
        )
    return d["densidad_g_ml"]


def resolver(e: ComponenteEntrada, c: Compuesto) -> tuple[float, float]:
    """Devuelve (gramos de material tal como se carga, fracción de esa masa que es el compuesto)."""
    pm = c.pm if c.pm_aplicable else 0.0
    fraccion = fraccion_masica(e.concentracion, pm, e.densidad_g_ml)
    if e.gramos is not None:
        return e.gramos, fraccion
    assert e.cantidad is not None  # garantizado por el esquema
    if e.unidad in MASA_G:
        return e.cantidad * MASA_G[e.unidad], fraccion
    if e.unidad in VOLUMEN_ML:
        return e.cantidad * VOLUMEN_ML[e.unidad] * _densidad_de_carga(e, c), fraccion
    # moles netos del compuesto
    if pm <= 0:
        raise ValueError(f"{c.nombre} no tiene peso molecular: no se puede informar en moles")
    neto = e.pureza / 100.0 * fraccion
    if neto <= 0:
        raise ValueError(f"{c.nombre}: con pureza {e.pureza:g} % no hay compuesto: no se puede obtener esa cantidad de moles")
    return e.cantidad * MOLES[e.unidad] * pm / neto, fraccion


def convertir(
    c: Compuesto,
    cantidad: float,
    unidad: str,
    a_unidad: str,
    pureza: float = 100.0,
    concentracion: Concentracion | None = None,
    densidad_g_ml: float | None = None,
) -> dict:
    """Convierte una cantidad de `c` entre unidades y devuelve el valor con los datos intermedios."""
    e = ComponenteEntrada(
        id=c.id, cantidad=cantidad, unidad=unidad, pureza=pureza, concentracion=concentracion, densidad_g_ml=densidad_g_ml
    )
    gramos, fraccion = resolver(e, c)
    neto_g = gramos * fraccion * pureza / 100.0
    if a_unidad in MASA_G:
        valor = gramos / MASA_G[a_unidad]
        rho = None
    elif a_unidad in VOLUMEN_ML:
        rho = _densidad_de_carga(e, c)
        valor = gramos / rho / VOLUMEN_ML[a_unidad]
    else:
        if not c.pm_aplicable or c.pm <= 0:
            raise ValueError(f"{c.nombre} no tiene peso molecular: no se puede informar en moles")
        valor = neto_g / c.pm / MOLES[a_unidad]
        rho = e.densidad_g_ml
    return {
        "compuesto_id": c.id,
        "valor": valor,
        "unidad": a_unidad,
        "gramos_material": gramos,
        "fraccion_soluto": fraccion,
        "gramos_compuesto_neto": neto_g,
        "moles_netos": neto_g / c.pm if c.pm_aplicable and c.pm > 0 else None,
        "densidad_g_ml": rho if rho is not None else e.densidad_g_ml,
    }
