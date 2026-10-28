import pytest

from app.core import formulas as f


@pytest.mark.parametrize(
    "formula,pm",
    [
        ("H2O", 18.015),
        ("C2H6O", 46.069),
        ("C13H18O2", 206.285),            # ibuprofeno
        ("Ca(OH)2", 74.093),
        ("Al2(SO4)3", 342.15),
        ("K4[Fe(CN)6]", 368.35),          # corchetes y paréntesis anidados
        ("CuSO4·5H2O", 249.685),          # hidrato
        ("Na2CO3·10H2O", 286.14),
        ("H₂SO₄", 98.07),                 # subíndices Unicode
    ],
)
def test_peso_molecular(formula, pm):
    assert f.peso_molecular(formula) == pytest.approx(pm, abs=0.02)


def test_composicion():
    assert dict(f.composicion("Ca(OH)2")) == {"Ca": 1, "O": 2, "H": 2}
    assert dict(f.composicion("CuSO4·5H2O")) == {"Cu": 1, "S": 1, "O": 9, "H": 10}


def test_formula_de_hill():
    assert f.formula_hill(f.composicion("OH2")) == "H2O"
    assert f.formula_hill(f.composicion("NaCl")) == "ClNa"
    assert f.formula_hill(f.composicion("C2H6O")) == "C2H6O"
    assert f.formula_hill(f.composicion("OC2H6")) == "C2H6O"


def test_composicion_porcentual_suma_100():
    comp = f.composicion_porcentual("C13H18O2")
    assert sum(x["masa_pct"] for x in comp) == pytest.approx(100.0, abs=0.01)
    assert comp[0]["simbolo"] == "C" and comp[0]["masa_pct"] == pytest.approx(75.69, abs=0.02)


@pytest.mark.parametrize("malo", ["", "Xx2", "H2O)", "(H2O", "h2o", "H2O$", "H0", "(C6H10O5)n"])
def test_formulas_invalidas(malo):
    with pytest.raises(f.FormulaInvalida):
        f.peso_molecular(malo)


def test_los_118_elementos_tienen_masa():
    masas = f.masas_atomicas()
    assert len(masas) == 118 and all(m > 0 for m in masas.values())
