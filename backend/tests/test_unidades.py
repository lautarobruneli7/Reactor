"""Unidades de cantidad y concentración: la pureza y la concentración son datos distintos."""
import pytest

from app.core import unidades
from app.core.simulador import cargar_reaccion, simular
from app.models.schemas import ComponenteEntrada as E, Concentracion


def _c(catalogo, id_):
    return catalogo[id_]


def test_masa_en_distintas_unidades(catalogo):
    e = E(id="naoh", cantidad=2, unidad="kg", pureza=100)
    assert unidades.resolver(e, _c(catalogo, "naoh")) == (2000.0, 1.0)
    assert unidades.resolver(E(id="naoh", cantidad=500, unidad="mg"), _c(catalogo, "naoh"))[0] == pytest.approx(0.5)


def test_volumen_de_liquido_puro_usa_la_densidad_del_catalogo(catalogo):
    d = unidades.densidad_pura("etanol")["densidad_g_ml"]
    g, f = unidades.resolver(E(id="etanol", cantidad=100, unidad="mL"), _c(catalogo, "etanol"))
    assert g == pytest.approx(100 * d) and f == 1.0
    g_l, _ = unidades.resolver(E(id="etanol", cantidad=0.1, unidad="L"), _c(catalogo, "etanol"))
    assert g_l == pytest.approx(g)


def test_densidad_informada_por_el_usuario_manda_sobre_la_del_catalogo(catalogo):
    g, _ = unidades.resolver(E(id="etanol", cantidad=10, unidad="mL", densidad_g_ml=0.80), _c(catalogo, "etanol"))
    assert g == pytest.approx(8.0)


def test_sin_densidad_no_se_inventa(catalogo):
    with pytest.raises(unidades.FaltaDensidad, match="densidad"):
        unidades.resolver(E(id="ibb", cantidad=10, unidad="mL"), _c(catalogo, "ibb"))  # sin dato confiable en el catálogo


def test_mililitros_de_una_solucion_exigen_la_densidad_de_la_solucion(catalogo):
    e = E(id="hcl", cantidad=100, unidad="mL", concentracion=Concentracion(tipo="p/p", valor=37))
    with pytest.raises(unidades.FaltaDensidad, match="solución"):
        unidades.resolver(e, _c(catalogo, "hcl"))
    g, f = unidades.resolver(e.model_copy(update={"densidad_g_ml": 1.19}), _c(catalogo, "hcl"))
    assert g == pytest.approx(119.0) and f == pytest.approx(0.37)


def test_hcl_37_pp_no_es_hcl_con_pureza_37(catalogo):
    """100 g de solución al 37 % p/p tienen 37 g de HCl; el resto es agua, no impureza."""
    hcl = _c(catalogo, "hcl")
    r = unidades.convertir(hcl, 100, "g", "mol", concentracion=Concentracion(tipo="p/p", valor=37))
    assert r["gramos_compuesto_neto"] == pytest.approx(37.0)
    assert r["moles_netos"] == pytest.approx(37.0 / hcl.pm)
    assert r["fraccion_soluto"] == pytest.approx(0.37)


def test_molaridad_y_p_v_con_densidad(catalogo):
    hcl = _c(catalogo, "hcl")
    w = unidades.fraccion_masica(Concentracion(tipo="molar", valor=12.0), hcl.pm, 1.19)
    assert w == pytest.approx(12.0 * hcl.pm / 1190.0)
    w2 = unidades.fraccion_masica(Concentracion(tipo="p/v", valor=44.0), hcl.pm, 1.19)
    assert w2 == pytest.approx(44.0 / 119.0)
    with pytest.raises(unidades.FaltaDensidad):
        unidades.fraccion_masica(Concentracion(tipo="molar", valor=1.0), hcl.pm, None)


def test_concentracion_imposible(catalogo):
    with pytest.raises(ValueError, match="imposible"):
        unidades.fraccion_masica(Concentracion(tipo="molar", valor=40.0), 36.46, 1.0)  # 146 % en masa
    with pytest.raises(ValueError, match="imposible"):
        unidades.fraccion_masica(Concentracion(tipo="p/p", valor=120), 36.46, None)


def test_moles_son_netos_y_descuentan_pureza(catalogo):
    naoh = _c(catalogo, "naoh")
    g, _ = unidades.resolver(E(id="naoh", cantidad=0.5, unidad="mol", pureza=100), naoh)
    assert g == pytest.approx(0.5 * naoh.pm)
    g98, _ = unidades.resolver(E(id="naoh", cantidad=0.5, unidad="mol", pureza=98), naoh)
    assert g98 == pytest.approx(0.5 * naoh.pm / 0.98)
    with pytest.raises(ValueError, match="no hay compuesto"):
        unidades.resolver(E(id="naoh", cantidad=1, unidad="mol", pureza=0), naoh)


def test_moles_de_un_polimero_no_se_pueden(catalogo):
    with pytest.raises(ValueError, match="peso molecular"):
        unidades.resolver(E(id="exc", cantidad=1, unidad="mol"), _c(catalogo, "exc"))


def test_ida_y_vuelta_de_unidades(catalogo):
    etanol = _c(catalogo, "etanol")
    ml = unidades.convertir(etanol, 2.0, "mol", "mL")["valor"]
    de_vuelta = unidades.convertir(etanol, ml, "mL", "mol")["valor"]
    assert de_vuelta == pytest.approx(2.0)


def test_convertir_concentracion_a_las_tres_formas(catalogo):
    hcl = _c(catalogo, "hcl")
    r = unidades.convertir_concentracion(Concentracion(tipo="p/p", valor=37), hcl.pm, 1.18)
    assert r["p_p_pct"] == pytest.approx(37)
    assert r["g_por_l"] == pytest.approx(0.37 * 1180)
    assert r["molar"] == pytest.approx(0.37 * 1180 / hcl.pm)
    assert r["p_v_pct"] == pytest.approx(0.37 * 118)
    sin_rho = unidades.convertir_concentracion(Concentracion(tipo="p/p", valor=37), hcl.pm, None)
    assert sin_rho["molar"] is None and sin_rho["p_p_pct"] == pytest.approx(37)


# ---------- dentro de la simulación ----------
def _neutralizacion(catalogo, hcl_entrada):
    return simular(
        [hcl_entrada, E(id="naoh", gramos=40.0, pureza=100)], catalogo, cargar_reaccion("neutralizacion-hcl-naoh")
    )


def test_solucion_en_la_simulacion_cuenta_solo_el_soluto(catalogo):
    # 98,54 g de solución al 37 % p/p = 36,46 g de HCl = 1 mol: neutraliza exactamente 1 mol de NaOH
    sol = E(id="hcl", gramos=36.46 / 0.37, pureza=100, concentracion=Concentracion(tipo="p/p", valor=37))
    out = _neutralizacion(catalogo, sol)
    r = out.resultado
    assert r.gramos_teoricos == pytest.approx(58.44, abs=0.03)
    assert all(abs(x.exceso_pct) < 0.2 for x in r.reactivos)
    hcl = next(x for x in r.reactivos if x.id == "hcl")
    assert hcl.fraccion_soluto == pytest.approx(0.37) and hcl.gramos_cargados == pytest.approx(36.46 / 0.37, abs=0.01)
    assert any(a.tipo == "info" and "solución" in a.mensaje for a in out.alertas)


def test_concentracion_no_se_confunde_con_impureza(catalogo):
    """Con concentración 37 % (pureza 100) el producto sale puro; con «pureza 37 %» se lo castiga como si fuera impuro."""
    cantidad = 36.46 / 0.37
    como_solucion = _neutralizacion(
        catalogo, E(id="hcl", gramos=cantidad, pureza=100, concentracion=Concentracion(tipo="p/p", valor=37))
    ).resultado
    como_pureza = _neutralizacion(catalogo, E(id="hcl", gramos=cantidad, pureza=37)).resultado
    assert como_solucion.pureza_producto_pct > 99
    assert como_pureza.pureza_producto_pct < como_solucion.pureza_producto_pct - 5
    # los moles son los mismos: lo que cambia es cómo se interpreta el resto de la masa
    assert como_solucion.moles_reaccion == pytest.approx(como_pureza.moles_reaccion, rel=1e-3)


def test_cantidades_en_moles_y_ml_en_la_simulacion(catalogo):
    out = simular(
        [E(id="hcl", cantidad=1, unidad="mol"), E(id="naoh", cantidad=1000, unidad="mmol")],
        catalogo, cargar_reaccion("neutralizacion-hcl-naoh"),
    )
    assert out.resultado.gramos_teoricos == pytest.approx(58.44, abs=0.03)
    assert out.resultado.reactivos[0].gramos_cargados == pytest.approx(36.46, abs=0.01)


def test_los_componentes_que_no_participan_no_exigen_densidad(catalogo):
    # el ibb no tiene densidad en el catálogo, pero no participa en la neutralización: no debe fallar
    out = simular(
        [E(id="hcl", gramos=36.46, pureza=100), E(id="naoh", gramos=40, pureza=100), E(id="ibb", cantidad=5, unidad="mL")],
        catalogo, cargar_reaccion("neutralizacion-hcl-naoh"),
    )
    assert out.resultado is not None


def test_las_cargas_resueltas_incluyen_catalizador_y_excipiente_en_gramos(mezcla_ejemplo, catalogo, reaccion):
    r = simular(mezcla_ejemplo, catalogo, reaccion).resultado
    por_id = {c.id: c for c in r.cargas}
    assert set(por_id) == {"ibb", "aa", "cat", "h2", "co", "exc"}
    assert por_id["cat"].gramos_material == pytest.approx(20.0)
    assert por_id["exc"].moles_netos is None  # polímero: sin peso molecular
    assert por_id["aa"].moles_netos == pytest.approx(102 * 0.98 / catalogo["aa"].pm, rel=1e-4)
