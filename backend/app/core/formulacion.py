"""Formulación: proporción de principio activo y excipientes en la mezcla final."""


def gramos_efectivos(gramos: float, pureza_pct: float) -> float:
    return gramos * pureza_pct / 100.0


def pct_principio_activo(gramos_activo: float, gramos_excipiente: float) -> float:
    """% en masa del principio activo sobre (activo + excipiente)."""
    total = gramos_activo + gramos_excipiente
    if total <= 0:
        return 0.0
    return gramos_activo / total * 100.0
