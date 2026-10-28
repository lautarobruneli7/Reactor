"""Balanceo de ecuaciones químicas por conservación de átomos.

Para cada elemento, los átomos que entran tienen que ser los que salen. Eso es
un sistema lineal homogéneo; sus soluciones enteras positivas más chicas son
los coeficientes. Se resuelve con aritmética exacta (fracciones), sin
aproximaciones de punto flotante.

Sirve para cualquier reacción cuyas fórmulas se puedan escribir, no solo las
del catálogo.
"""
from fractions import Fraction
from math import gcd

from app.core.formulas import composicion


class NoBalanceable(ValueError):
    """La ecuación no se puede balancear (o tiene infinitas soluciones)."""


def _espacio_nulo(matriz: list[list[Fraction]]) -> list[list[Fraction]]:
    """Base del espacio nulo de la matriz (eliminación de Gauss-Jordan exacta)."""
    filas, columnas = len(matriz), len(matriz[0])
    m = [fila[:] for fila in matriz]
    pivotes: list[int] = []
    r = 0
    for c in range(columnas):
        if r >= filas:
            break
        p = next((i for i in range(r, filas) if m[i][c] != 0), None)
        if p is None:
            continue
        m[r], m[p] = m[p], m[r]
        piv = m[r][c]
        m[r] = [x / piv for x in m[r]]
        for i in range(filas):
            if i != r and m[i][c] != 0:
                f = m[i][c]
                m[i] = [a - f * b for a, b in zip(m[i], m[r])]
        pivotes.append(c)
        r += 1
    libres = [c for c in range(columnas) if c not in pivotes]
    base = []
    for lib in libres:
        v = [Fraction(0)] * columnas
        v[lib] = Fraction(1)
        for fila, pc in enumerate(pivotes):
            v[pc] = -m[fila][lib]
        base.append(v)
    return base


def _a_enteros(v: list[Fraction]) -> list[int]:
    from math import lcm

    den = 1
    for x in v:
        den = lcm(den, x.denominator)
    enteros = [int(x * den) for x in v]
    g = 0
    for x in enteros:
        g = gcd(g, abs(x))
    return [x // g for x in enteros] if g else enteros


def balancear(reactivos: list[str], productos: list[str]) -> tuple[list[int], list[int]]:
    """Devuelve (coeficientes de reactivos, coeficientes de productos)."""
    if not reactivos or not productos:
        raise NoBalanceable("Hace falta al menos un reactivo y un producto")
    especies = reactivos + productos
    comps = [composicion(f) for f in especies]
    elementos = sorted({el for c in comps for el in c})
    for el in elementos:
        en_reactivos = any(el in comps[i] for i in range(len(reactivos)))
        en_productos = any(el in comps[i] for i in range(len(reactivos), len(especies)))
        if en_reactivos != en_productos:
            lado = "los reactivos" if en_reactivos else "los productos"
            raise NoBalanceable(f"El elemento {el} aparece solo en {lado}: no se puede balancear")

    signo = [1] * len(reactivos) + [-1] * len(productos)
    matriz = [[Fraction(signo[j] * comps[j].get(el, 0)) for j in range(len(especies))] for el in elementos]
    base = _espacio_nulo(matriz)
    if not base:
        raise NoBalanceable("No existe una combinación de coeficientes que conserve los átomos")
    if len(base) > 1:
        raise NoBalanceable(
            "La ecuación admite infinitas soluciones independientes (hay reacciones simultáneas posibles): "
            "agregá o quitá especies para que quede una sola reacción"
        )
    coef = _a_enteros(base[0])
    if all(c < 0 for c in coef):
        coef = [-c for c in coef]
    if any(c <= 0 for c in coef):
        raise NoBalanceable("La única solución tiene coeficientes negativos o cero: esas especies no pueden reaccionar así")
    return coef[: len(reactivos)], coef[len(reactivos):]


def esta_balanceada(reactivos: list[tuple[str, int]], productos: list[tuple[str, int]]) -> bool:
    """Comprueba que una ecuación con coeficientes dados conserva los átomos."""
    from collections import Counter

    def total(lado: list[tuple[str, int]]) -> Counter:
        t: Counter = Counter()
        for formula, coef in lado:
            for el, n in composicion(formula).items():
                t[el] += n * coef
        return t

    return total(reactivos) == total(productos)


def ecuacion_texto(reactivos: list[tuple[str, int]], productos: list[tuple[str, int]]) -> str:
    def lado(items: list[tuple[str, int]]) -> str:
        return " + ".join(f"{c if c != 1 else ''}{'' if c == 1 else ' '}{f}" for f, c in items)

    return f"{lado(reactivos)} → {lado(productos)}"
