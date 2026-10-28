import pytest

from app.core.balanceo import NoBalanceable, balancear, esta_balanceada


@pytest.mark.parametrize(
    "reactivos,productos,esperado",
    [
        (["H2", "O2"], ["H2O"], ([2, 1], [2])),
        (["C3H8", "O2"], ["CO2", "H2O"], ([1, 5], [3, 4])),
        (["Fe2O3", "CO"], ["Fe", "CO2"], ([1, 3], [2, 3])),
        (["KMnO4", "HCl"], ["KCl", "MnCl2", "Cl2", "H2O"], ([2, 16], [2, 2, 5, 8])),
        (["Al", "H2SO4"], ["Al2(SO4)3", "H2"], ([2, 3], [1, 3])),
        (["C6H12O6", "O2"], ["CO2", "H2O"], ([1, 6], [6, 6])),
        (["CuO", "H2SO4", "H2O"], ["CuSO4·5H2O"], ([1, 1, 4], [1])),
    ],
)
def test_balancea(reactivos, productos, esperado):
    assert balancear(reactivos, productos) == esperado


def test_resultado_conserva_atomos():
    cr, cp = balancear(["C3H8", "O2"], ["CO2", "H2O"])
    assert esta_balanceada(list(zip(["C3H8", "O2"], cr)), list(zip(["CO2", "H2O"], cp)))
    assert not esta_balanceada([("H2", 1), ("O2", 1)], [("H2O", 1)])


def test_elemento_que_solo_aparece_de_un_lado():
    with pytest.raises(NoBalanceable, match="solo en"):
        balancear(["H2"], ["NaCl"])


def test_infinitas_soluciones():
    with pytest.raises(NoBalanceable, match="infinitas"):
        balancear(["H2", "O2"], ["H2O", "H2O2"])


def test_sin_especies():
    with pytest.raises(NoBalanceable):
        balancear([], ["H2O"])


def test_ecuacion_global_del_ibuprofeno_conserva_atomos_pero_no_es_unica():
    """Con 6 especies y solo C, H y O, hay varias ecuaciones posibles: el balanceador lo avisa en vez de elegir una."""
    r = [("C10H14", 1), ("C4H6O3", 1), ("H2", 1), ("CO", 1)]
    p = [("C13H18O2", 1), ("C2H4O2", 1)]
    assert esta_balanceada(r, p)
    with pytest.raises(NoBalanceable, match="infinitas"):
        balancear([f for f, _ in r], [f for f, _ in p])
