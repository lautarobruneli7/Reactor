"""Fórmulas químicas: lectura, composición elemental y peso molecular.

Sirve para cualquier sustancia, no solo las del catálogo: alcanza con escribir
la fórmula. Acepta paréntesis y corchetes anidados (Ca(OH)2, K4[Fe(CN)6]),
hidratos (CuSO4·5H2O) y subíndices Unicode (H₂O).

El peso molecular se calcula con las masas atómicas de data/elementos.json
(NIST, vía la librería `periodictable`): es un cálculo, no un valor tipeado.
"""
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_SUBINDICES = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SEPARADOR_HIDRATO = re.compile(r"[·•*]")
_TOKEN = re.compile(r"[A-Z][a-z]?|\d+|[()\[\]]")


class FormulaInvalida(ValueError):
    """La fórmula no se puede interpretar."""


@lru_cache(maxsize=1)
def masas_atomicas() -> dict[str, float]:
    with open(DATA_DIR / "elementos.json", encoding="utf-8") as f:
        return {e["simbolo"]: e["masa_atomica"] for e in json.load(f)}


def _parsear_parte(texto: str) -> Counter:
    masas = masas_atomicas()
    if not texto:
        raise FormulaInvalida("Fórmula vacía")
    if "".join(_TOKEN.findall(texto)) != texto:
        raro = re.sub(_TOKEN, "", texto)
        raise FormulaInvalida(f"Caracteres no válidos en la fórmula: {raro!r}")

    pila: list[Counter] = [Counter()]
    cierres: list[str] = []
    tokens = _TOKEN.findall(texto)
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in "([":
            pila.append(Counter())
            cierres.append(")" if t == "(" else "]")
            i += 1
        elif t in ")]":
            if not cierres or cierres.pop() != t:
                raise FormulaInvalida("Paréntesis desbalanceados")
            grupo = pila.pop()
            mult = 1
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                mult = int(tokens[i + 1])
                i += 1
            for el, n in grupo.items():
                pila[-1][el] += n * mult
            i += 1
        elif t.isdigit():
            raise FormulaInvalida(f"Número inesperado ({t}) en la fórmula")
        else:
            if t not in masas:
                raise FormulaInvalida(f"Elemento desconocido: {t}")
            n = 1
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                n = int(tokens[i + 1])
                i += 1
            if n == 0:
                raise FormulaInvalida("Un subíndice no puede ser cero")
            pila[-1][t] += n
            i += 1
    if cierres:
        raise FormulaInvalida("Paréntesis desbalanceados")
    return pila[0]


def composicion(formula: str) -> Counter:
    """{'C': 2, 'H': 6, 'O': 1} para 'C2H6O'. Soporta hidratos y paréntesis."""
    texto = formula.strip().translate(_SUBINDICES).replace(" ", "")
    if not texto:
        raise FormulaInvalida("Fórmula vacía")
    total: Counter = Counter()
    for parte in _SEPARADOR_HIDRATO.split(texto):
        m = re.match(r"^(\d+)(.*)$", parte)
        mult, resto = (int(m.group(1)), m.group(2)) if m else (1, parte)
        for el, n in _parsear_parte(resto).items():
            total[el] += n * mult
    return total


def peso_molecular(formula: str) -> float:
    """Peso molecular en g/mol."""
    masas = masas_atomicas()
    return sum(masas[el] * n for el, n in composicion(formula).items())


def formula_hill(comp: Counter) -> str:
    """Fórmula en notación de Hill: C primero, H después, el resto alfabético."""
    def parte(el: str) -> str:
        n = comp[el]
        return el if n == 1 else f"{el}{n}"

    elementos = sorted(comp)
    if "C" in comp:
        orden = ["C"] + (["H"] if "H" in comp else []) + [e for e in elementos if e not in ("C", "H")]
    else:
        orden = elementos
    return "".join(parte(e) for e in orden)


def composicion_porcentual(formula: str) -> list[dict]:
    """Porcentaje en masa de cada elemento (útil para análisis elemental)."""
    masas = masas_atomicas()
    comp = composicion(formula)
    pm = peso_molecular(formula)
    return [
        {"simbolo": el, "atomos": n, "masa_pct": round(masas[el] * n / pm * 100, 3)}
        for el, n in sorted(comp.items(), key=lambda kv: (kv[0] != "C", kv[0] != "H", kv[0]))
    ]
