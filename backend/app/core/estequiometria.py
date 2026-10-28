"""Estequiometría: moles útiles, reactivo limitante y rendimiento teórico.

Convención: se trabaja en moles internamente; los gramos se usan solo para
entrada y salida.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Reactivo:
    id: str
    nombre: str
    gramos: float
    pureza: float  # %
    pm: float  # g/mol
    coef: int  # coeficiente estequiométrico
    fraccion: float = 1.0  # fracción de la masa cargada que es el compuesto (solución: 0,37 para HCl 37 % p/p)

    @property
    def moles_utiles(self) -> float:
        return moles_utiles(self.gramos * self.fraccion, self.pureza, self.pm)

    @property
    def moles_equivalentes(self) -> float:
        """Moles de producto que este reactivo permitiría formar por sí solo."""
        return self.moles_utiles / self.coef if self.coef else float("inf")


def moles_utiles(gramos: float, pureza_pct: float, pm: float) -> float:
    """Moles reales de sustancia, corrigiendo la masa por la pureza del insumo."""
    if pm <= 0:
        raise ValueError("El peso molecular debe ser mayor que cero")
    return (gramos * pureza_pct / 100.0) / pm


def reactivo_limitante(reactivos: list[Reactivo]) -> Reactivo:
    """Reactivo que se agota primero (menor cantidad de moles equivalentes)."""
    if not reactivos:
        raise ValueError("Se necesita al menos un reactivo")
    return min(reactivos, key=lambda r: r.moles_equivalentes)


def gramos_de_producto(moles_producto: float, pm_producto: float) -> float:
    return moles_producto * pm_producto


def exceso_relativo(reactivo: Reactivo, moles_teoricos: float) -> float:
    """Exceso de un reactivo respecto del limitante (0.25 = 25 % de sobra)."""
    if moles_teoricos <= 0:
        return 0.0
    return reactivo.moles_equivalentes / moles_teoricos - 1.0


def economia_atomica(pm_producto: float, coef_producto: int, reactivos: list[tuple[float, int]]) -> float:
    """Economía atómica (%): masa del producto deseado / masa de todos los reactivos, según la ecuación.

    `reactivos` es una lista de (peso molecular, coeficiente). No depende de las cantidades cargadas.
    """
    total = sum(pm * coef for pm, coef in reactivos)
    if total <= 0:
        return 0.0
    return pm_producto * coef_producto / total * 100.0
