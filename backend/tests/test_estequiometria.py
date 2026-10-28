import pytest

from app.core import estequiometria as est


def test_moles_utiles_corrige_por_pureza():
    # 100 g al 98 % de un compuesto de PM 100 -> 0,98 mol
    assert est.moles_utiles(100, 98, 100) == pytest.approx(0.98)


def test_moles_utiles_rechaza_pm_cero():
    with pytest.raises(ValueError):
        est.moles_utiles(10, 100, 0)


def test_reactivo_limitante_es_el_de_menos_moles_equivalentes():
    a = est.Reactivo("a", "A", gramos=100, pureza=100, pm=100, coef=1)  # 1 mol
    b = est.Reactivo("b", "B", gramos=100, pureza=100, pm=50, coef=1)   # 2 mol
    c = est.Reactivo("c", "C", gramos=100, pureza=100, pm=100, coef=2)  # 0,5 mol equiv.
    assert est.reactivo_limitante([a, b]).id == "a"
    assert est.reactivo_limitante([a, b, c]).id == "c"


def test_exceso_relativo():
    r = est.Reactivo("a", "A", gramos=125, pureza=100, pm=100, coef=1)  # 1,25 mol
    assert est.exceso_relativo(r, moles_teoricos=1.0) == pytest.approx(0.25)


def test_exceso_relativo_sin_moles_teoricos():
    r = est.Reactivo("a", "A", gramos=10, pureza=100, pm=100, coef=1)
    assert est.exceso_relativo(r, moles_teoricos=0) == 0.0
