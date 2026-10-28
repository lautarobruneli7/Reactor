"""Efecto de la pureza de los insumos y del catalizador sobre el producto."""
from app.models.schemas import ParametrosModelo


def factor_catalizador(ratio: float, p: ParametrosModelo) -> float:
    """Penaliza el desvío respecto de la relación molar óptima catalizador/limitante.

    Si la reacción no define una relación óptima, el catalizador no penaliza por cantidad.
    """
    if p.catalizador_ratio_optimo is None:
        return 1.0
    desvio = abs(ratio - p.catalizador_ratio_optimo) / p.catalizador_ratio_optimo
    return max(p.factor_catalizador_minimo, 1 - desvio * p.pendiente_catalizador)


def factor_exceso(exceso_max: float, p: ParametrosModelo) -> float:
    """Penaliza el exceso de reactivos (más sobrante = más pérdidas de purificación)."""
    return max(
        p.factor_exceso_minimo,
        1 - max(0.0, exceso_max - p.exceso_tolerado) * p.pendiente_exceso,
    )


def impureza_media(purezas: list[float]) -> float:
    """Impureza media (%) de los insumos."""
    if not purezas:
        return 0.0
    return sum(100.0 - x for x in purezas) / len(purezas)


def pureza_producto(
    purezas_reactivos: list[float], factor_cat: float, p: ParametrosModelo
) -> float:
    """Pureza estimada del producto (%), acotada al rango del modelo."""
    valor = (
        100.0
        - impureza_media(purezas_reactivos) * p.penalizacion_impureza
        - (1 - factor_cat) * p.penalizacion_catalizador_pureza
    )
    return max(p.pureza_producto_minima, min(p.pureza_producto_maxima, valor))
