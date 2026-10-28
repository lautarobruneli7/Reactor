"""El motor en Python tiene que dar los mismos números que el prototipo HTML."""
import pytest

from app.core.simulador import ComponenteDesconocido, simular
from app.models.schemas import ComponenteEntrada


def test_mezcla_ejemplo_coincide_con_el_prototipo(mezcla_ejemplo, catalogo, reaccion):
    out = simular(mezcla_ejemplo, catalogo, reaccion)
    r = out.resultado
    assert r is not None
    assert r.puntaje == 85
    assert r.categoria == "Excelente"
    assert r.rendimiento_pct == pytest.approx(84.7, abs=0.1)
    assert r.pureza_producto_pct == pytest.approx(97.6, abs=0.1)
    assert r.balance_pct == pytest.approx(99, abs=1)
    assert r.reactivo_limitante == "Anhídrido acético"
    assert r.gramos_teoricos == pytest.approx(202.0, abs=0.1)
    assert r.gramos_estimados == pytest.approx(171.1, abs=0.1)
    assert r.pct_principio_activo == pytest.approx(85.2, abs=0.1)
    assert not r.cumple_pureza  # 97,6 % < 98,5 % orientativo


def test_poco_catalizador_baja_el_puntaje(mezcla_ejemplo, catalogo, reaccion):
    # Mismo caso que en el prototipo: el catalizador pasa de 20 g a 60 g
    for c in mezcla_ejemplo:
        if c.id == "cat":
            c.gramos = 60
    r = simular(mezcla_ejemplo, catalogo, reaccion).resultado
    assert r.puntaje == 56
    assert r.rendimiento_pct == pytest.approx(34.0, abs=0.1)
    assert r.pureza_producto_pct == pytest.approx(95.2, abs=0.1)


def test_sin_catalizador_penaliza_y_avisa(mezcla_ejemplo, catalogo, reaccion):
    sin_cat = [c for c in mezcla_ejemplo if c.id != "cat"]
    out = simular(sin_cat, catalogo, reaccion)
    assert out.resultado is not None
    assert any(a.tipo == "bad" and "catalizador" in a.mensaje for a in out.alertas)


def test_sin_excipiente_no_calcula_formulacion(mezcla_ejemplo, catalogo, reaccion):
    sin_exc = [c for c in mezcla_ejemplo if c.id != "exc"]
    out = simular(sin_exc, catalogo, reaccion)
    assert out.resultado.pct_principio_activo is None
    assert any("excipiente" in a.mensaje for a in out.alertas)


def test_faltan_reactivos_no_hay_resultado(catalogo, reaccion):
    out = simular([ComponenteEntrada(id="ibb", gramos=100, pureza=98)], catalogo, reaccion)
    assert out.resultado is None
    assert out.alertas and out.alertas[0].tipo == "warn"


def test_reactivo_en_cero_no_rompe(mezcla_ejemplo, catalogo, reaccion):
    for c in mezcla_ejemplo:
        if c.id == "aa":
            c.gramos = 0
    out = simular(mezcla_ejemplo, catalogo, reaccion)
    assert out.resultado is None
    assert any(a.tipo == "bad" for a in out.alertas)


def test_exceso_grande_genera_alerta(mezcla_ejemplo, catalogo, reaccion):
    for c in mezcla_ejemplo:
        if c.id == "ibb":
            c.gramos = 300
    out = simular(mezcla_ejemplo, catalogo, reaccion)
    assert any("Gran exceso" in a.mensaje for a in out.alertas)


def test_compuesto_desconocido(catalogo, reaccion):
    with pytest.raises(ComponenteDesconocido):
        simular([ComponenteEntrada(id="xxx", gramos=1, pureza=100)], catalogo, reaccion)


def test_compuesto_repetido(catalogo, reaccion):
    dup = [ComponenteEntrada(id="ibb", gramos=1, pureza=100)] * 2
    with pytest.raises(ValueError):
        simular(dup, catalogo, reaccion)
