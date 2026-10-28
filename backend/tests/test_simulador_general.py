"""El motor tiene que servir para cualquier reacción del catálogo, no solo para el ibuprofeno."""
import pytest

from app.core.simulador import cargar_reaccion, simular
from app.models.schemas import ComponenteEntrada as E


def _sim(catalogo, reaccion_id, mezcla, **kw):
    return simular([E(id=i, gramos=g, pureza=p) for i, g, p in mezcla], catalogo, cargar_reaccion(reaccion_id), **kw)


def test_neutralizacion_en_proporcion_exacta(catalogo):
    out = _sim(catalogo, "neutralizacion-hcl-naoh", [("hcl", 36.46, 100), ("naoh", 40.00, 100)])
    r = out.resultado
    assert r.gramos_teoricos == pytest.approx(58.44, abs=0.02)         # 1 mol de NaCl
    assert r.economia_atomica_pct == pytest.approx(76.43, abs=0.05)
    nacl, agua = r.productos
    assert (nacl.id, agua.id) == ("nacl", "agua")
    assert agua.gramos_teoricos == pytest.approx(18.02, abs=0.02)
    assert all(x.exceso_pct == pytest.approx(0, abs=0.1) for x in r.reactivos)
    assert r.ecuacion == "HCl + NaOH → NaCl + H2O"


def test_masa_se_conserva(catalogo):
    """Lo que se consume tiene que ser igual a lo que se produce (a rendimiento teórico)."""
    for rid, mezcla in {
        "neutralizacion-h2so4-naoh": [("h2so4", 98.07, 100), ("naoh", 80.0, 100)],
        "combustion-metano": [("metano", 16.04, 100), ("o2", 64.0, 100)],
        "zinc-acido-clorhidrico": [("zinc", 65.38, 100), ("hcl", 72.92, 100)],
        "calcinacion-carbonato-calcio": [("caco3", 100.09, 100)],
    }.items():
        r = _sim(catalogo, rid, mezcla).resultado
        consumido = sum(x.gramos_consumidos for x in r.reactivos)
        producido = sum(x.gramos_teoricos for x in r.productos)
        assert consumido == pytest.approx(producido, rel=2e-3), rid


def test_aspirina_limitante_y_exceso(catalogo):
    out = _sim(catalogo, "aspirina-acetilacion", [("acido-salicilico", 150.0, 100), ("aa", 102.09, 100)])
    r = out.resultado
    assert r.reactivo_limitante == "Anhídrido acético"
    assert r.gramos_teoricos == pytest.approx(180.16, abs=0.05)
    assert r.economia_atomica_pct == pytest.approx(75.0, abs=0.1)
    sal = next(x for x in r.reactivos if x.id == "acido-salicilico")
    assert sal.exceso_pct == pytest.approx(8.6, abs=0.1)
    assert sal.gramos_sobrantes == pytest.approx(150.0 - 138.12, abs=0.05)
    assert next(x for x in r.reactivos if x.limitante).id == "aa"


def test_la_pureza_de_los_insumos_cambia_el_limitante(catalogo):
    # 100 g de cada uno al 100 %: el de menor masa molar por coeficiente sobra, el otro limita
    puro = _sim(catalogo, "aspirina-acetilacion", [("acido-salicilico", 100, 100), ("aa", 100, 100)]).resultado
    impuro = _sim(catalogo, "aspirina-acetilacion", [("acido-salicilico", 100, 100), ("aa", 100, 60)]).resultado
    assert puro.reactivo_limitante == "Ácido salicílico"
    assert impuro.reactivo_limitante == "Anhídrido acético"


def test_coeficientes_distintos_de_uno(catalogo):
    # N2 + 3 H2 -> 2 NH3: con 1 mol de N2 y 3 mol de H2 salen 2 mol de NH3
    r = _sim(catalogo, "haber-bosch", [("n2", 28.01, 100), ("h2", 6.06, 100)]).resultado
    assert r.gramos_teoricos == pytest.approx(34.06, abs=0.05)
    assert r.moles_reaccion == pytest.approx(1.0, abs=0.002)
    assert r.productos[0].coef == 2


def test_catalizador_no_requerido_solo_avisa(catalogo):
    out = _sim(catalogo, "haber-bosch", [("n2", 28.01, 100), ("h2", 6.06, 100)])
    avisos = [a for a in out.alertas if "hierro" in a.mensaje.lower()]
    assert avisos and avisos[0].tipo == "warn"
    con = _sim(catalogo, "haber-bosch", [("n2", 28.01, 100), ("h2", 6.05, 100), ("hierro", 5, 100)])
    assert not any("hierro" in a.mensaje.lower() for a in con.alertas)


def test_reaccion_sin_catalizador_ni_excipiente_no_avisa_de_ellos(catalogo):
    out = _sim(catalogo, "neutralizacion-hcl-naoh", [("hcl", 36.46, 100), ("naoh", 40, 100)])
    assert not any("catalizador" in a.mensaje.lower() or "excipiente" in a.mensaje.lower() for a in out.alertas)
    assert out.resultado.pct_principio_activo is None


def test_rendimiento_experimental_reemplaza_al_del_modelo(catalogo):
    modelo = _sim(catalogo, "aspirina-acetilacion", [("acido-salicilico", 138.12, 100), ("aa", 102.09, 100)]).resultado
    real = _sim(catalogo, "aspirina-acetilacion", [("acido-salicilico", 138.12, 100), ("aa", 102.09, 100)],
                rendimiento_real_pct=60).resultado
    assert modelo.rendimiento_origen == "modelo" and real.rendimiento_origen == "experimental"
    assert real.rendimiento_pct == 60
    assert real.gramos_estimados == pytest.approx(real.gramos_teoricos * 0.6, abs=0.02)


def test_componente_que_no_participa_se_ignora_con_aviso(catalogo):
    out = _sim(catalogo, "neutralizacion-hcl-naoh", [("hcl", 36.46, 100), ("naoh", 40, 100), ("etanol", 50, 100)])
    assert any("etanol" in a.mensaje.lower() or "Etanol" in a.mensaje for a in out.alertas if a.tipo == "warn")
    assert out.resultado.gramos_teoricos == pytest.approx(58.44, abs=0.02)


def test_faltan_reactivos_de_otra_reaccion(catalogo):
    out = _sim(catalogo, "combustion-metano", [("metano", 10, 100)])
    assert out.resultado is None and "2 reactivos" in out.alertas[-1].mensaje


def test_reaccion_con_un_solo_reactivo(catalogo):
    r = _sim(catalogo, "calcinacion-carbonato-calcio", [("caco3", 100.09, 100)]).resultado
    assert r.reactivo_limitante == "Carbonato de calcio"
    assert r.gramos_teoricos == pytest.approx(56.08, abs=0.03)
    assert next(x for x in r.productos if x.id == "co2").gramos_teoricos == pytest.approx(44.01, abs=0.03)


def test_hidrato_como_producto(catalogo):
    r = _sim(catalogo, "sulfato-cobre-pentahidratado",
             [("cuo", 79.55, 100), ("h2so4", 98.07, 100), ("agua", 72.08, 100)]).resultado
    assert r.gramos_teoricos == pytest.approx(249.68, abs=0.05)


def test_polimero_no_puede_ser_reactivo(catalogo):
    from app.models.schemas import Participante

    mala = cargar_reaccion("neutralizacion-hcl-naoh").model_copy(deep=True)
    mala.reactivos = [Participante(id="exc", coef=1), Participante(id="naoh", coef=1)]
    with pytest.raises(ValueError, match="peso molecular"):
        simular([E(id="exc", gramos=10, pureza=100), E(id="naoh", gramos=10, pureza=100)], catalogo, mala)
