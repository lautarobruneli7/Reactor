import pytest

from app.core import calidad, formulacion, pureza


@pytest.mark.parametrize(
    "puntaje,esperada",
    [(100, "Excelente"), (85, "Excelente"), (84, "Buena"), (70, "Buena"),
     (69, "Regular"), (50, "Regular"), (49, "Deficiente"), (0, "Deficiente")],
)
def test_categoria(puntaje, esperada):
    assert calidad.categoria(puntaje) == esperada


def test_cumple_pureza():
    assert calidad.cumple_pureza(98.5, 98.5)
    assert not calidad.cumple_pureza(98.4, 98.5)


def test_pct_principio_activo():
    assert formulacion.pct_principio_activo(80, 20) == pytest.approx(80.0)
    assert formulacion.pct_principio_activo(0, 0) == 0.0


def test_pureza_producto_esta_acotada(reaccion):
    p = reaccion.parametros
    assert pureza.pureza_producto([100, 100], 1.0, p) == p.pureza_producto_maxima
    assert pureza.pureza_producto([50, 50], 0.4, p) == p.pureza_producto_minima


def test_factor_catalizador_es_maximo_en_el_optimo(reaccion):
    p = reaccion.parametros
    assert pureza.factor_catalizador(p.catalizador_ratio_optimo, p) == pytest.approx(1.0)
    assert pureza.factor_catalizador(0.5, p) < 1.0
