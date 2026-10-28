"""Puntaje de calidad (0-100) y cumplimiento de especificaciones.

IMPORTANTE: mide la calidad de la mezcla y del producto estimado (rendimiento,
pureza, balance estequiométrico). NO mide eficacia clínica: esa depende de la
dosis, la biodisponibilidad, la farmacocinética y los ensayos clínicos.
"""
from app.models.schemas import ParametrosModelo


def subpuntajes(
    rendimiento: float, pureza: float, exceso_max: float, p: ParametrosModelo
) -> tuple[float, float, float]:
    """Devuelve (rendimiento, pureza, balance), cada uno de 0 a 100 o más."""
    s_rend = rendimiento / p.rendimiento_maximo * 100.0
    s_pureza = max(0.0, (pureza - 90.0) / (100.0 - 90.0) * 100.0)
    s_balance = max(0.0, 100.0 - exceso_max * 150.0)
    return s_rend, s_pureza, s_balance


def puntaje_calidad(
    rendimiento: float, pureza: float, exceso_max: float, p: ParametrosModelo
) -> int:
    s_rend, s_pureza, s_balance = subpuntajes(rendimiento, pureza, exceso_max, p)
    w = p.pesos_puntaje
    bruto = s_rend * w.rendimiento + s_pureza * w.pureza + s_balance * w.balance
    return int(min(100.0, max(0.0, bruto)) + 0.5)  # redondeo "hacia arriba" en .5


def categoria(puntaje: int) -> str:
    if puntaje >= 85:
        return "Excelente"
    if puntaje >= 70:
        return "Buena"
    if puntaje >= 50:
        return "Regular"
    return "Deficiente"


def cumple_pureza(pureza: float, minimo: float) -> bool:
    return pureza >= minimo
