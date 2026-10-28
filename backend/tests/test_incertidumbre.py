"""Incertidumbre por Monte Carlo: reproducible, honesta sobre lo que cubre y sensata en los casos límite."""
import statistics

import pytest

from app.core import incertidumbre
from app.core.simulador import simular
from app.models.schemas import ParametrosIncertidumbre, SimulacionEntrada


def _entrada(mezcla, **kw):
    return SimulacionEntrada(componentes=mezcla, **kw)


def _analizar(mezcla, catalogo, reaccion, params=None, **kw):
    entrada = _entrada(mezcla, **kw)
    return incertidumbre.analizar(entrada, catalogo, reaccion, params or ParametrosIncertidumbre(n=400))


def test_misma_semilla_mismo_resultado(mezcla_ejemplo, catalogo, reaccion):
    a = _analizar(mezcla_ejemplo, catalogo, reaccion)
    b = _analizar(mezcla_ejemplo, catalogo, reaccion)
    assert a == b
    c = _analizar(mezcla_ejemplo, catalogo, reaccion, ParametrosIncertidumbre(n=400, semilla=7))
    assert c.rendimiento_pct != a.rendimiento_pct


def test_el_intervalo_contiene_el_valor_puntual(mezcla_ejemplo, catalogo, reaccion):
    base = simular(mezcla_ejemplo, catalogo, reaccion).resultado
    inc = _analizar(mezcla_ejemplo, catalogo, reaccion, ParametrosIncertidumbre(n=1000, sd_masa_rel_pct=1.0, sd_pureza_pts=1.0))
    for nombre, valor in (("rendimiento_pct", base.rendimiento_pct), ("pureza_producto_pct", base.pureza_producto_pct),
                          ("gramos_estimados", base.gramos_estimados)):
        iv = getattr(inc, nombre)
        assert iv.p5 <= iv.p50 <= iv.p95, nombre
        assert iv.p5 - 1e-9 <= valor <= iv.p95 + 1e-9, (nombre, valor, iv)
    assert inc.corridas_validas > 900


def test_sin_incertidumbre_en_las_entradas_no_hay_dispersion(mezcla_ejemplo, catalogo, reaccion):
    base = simular(mezcla_ejemplo, catalogo, reaccion).resultado
    inc = _analizar(mezcla_ejemplo, catalogo, reaccion, ParametrosIncertidumbre(n=300, sd_masa_rel_pct=0, sd_pureza_pts=0))
    assert inc.rendimiento_pct.sd == 0 and inc.pureza_producto_pct.sd == 0
    assert inc.rendimiento_pct.p50 == pytest.approx(base.rendimiento_pct)
    assert inc.puntaje.p50 == base.puntaje


def test_mas_error_de_balanza_ensancha_el_intervalo(mezcla_ejemplo, catalogo, reaccion):
    chico = _analizar(mezcla_ejemplo, catalogo, reaccion, ParametrosIncertidumbre(n=600, sd_masa_rel_pct=0.2, sd_pureza_pts=0))
    grande = _analizar(mezcla_ejemplo, catalogo, reaccion, ParametrosIncertidumbre(n=600, sd_masa_rel_pct=3.0, sd_pureza_pts=0))
    assert grande.gramos_estimados.sd > chico.gramos_estimados.sd * 3


def test_el_rendimiento_del_modelo_avisa_que_no_cubre_el_error_del_modelo(mezcla_ejemplo, catalogo, reaccion):
    inc = _analizar(mezcla_ejemplo, catalogo, reaccion)
    assert inc.incluye_incertidumbre_del_modelo is False
    assert any("NO incluye" in n for n in inc.notas)
    con = _analizar(mezcla_ejemplo, catalogo, reaccion, ParametrosIncertidumbre(n=600, sd_rendimiento_pts=5.0))
    assert con.incluye_incertidumbre_del_modelo is True
    assert con.rendimiento_pct.sd == pytest.approx(5.0, abs=1.0)
    assert not any("NO incluye" in n for n in con.notas)


def test_replicas_dan_el_desvio_del_laboratorio(mezcla_ejemplo, catalogo, reaccion):
    replicas = [78.0, 82.0, 80.0, 84.0, 76.0]
    inc = _analizar(
        mezcla_ejemplo, catalogo, reaccion, ParametrosIncertidumbre(n=1500, sd_masa_rel_pct=0, sd_pureza_pts=0),
        rendimiento_replicas_pct=replicas,
    )
    assert inc.incluye_incertidumbre_del_modelo is True
    assert inc.rendimiento_pct.media == pytest.approx(statistics.fmean(replicas), abs=0.5)
    assert inc.rendimiento_pct.sd == pytest.approx(statistics.stdev(replicas), abs=0.4)
    assert inc.supuestos["sd_rendimiento_pts"] == pytest.approx(statistics.stdev(replicas))


def test_un_solo_rendimiento_medido_no_tiene_variabilidad_y_lo_dice(mezcla_ejemplo, catalogo, reaccion):
    inc = _analizar(mezcla_ejemplo, catalogo, reaccion, ParametrosIncertidumbre(n=300, sd_masa_rel_pct=0, sd_pureza_pts=0),
                    rendimiento_real_pct=80)
    assert inc.rendimiento_pct.sd == 0 and inc.rendimiento_pct.p50 == 80
    assert any("réplicas" in n for n in inc.notas)


def test_pureza_medida_con_su_desvio(mezcla_ejemplo, catalogo, reaccion):
    inc = _analizar(
        mezcla_ejemplo, catalogo, reaccion,
        ParametrosIncertidumbre(n=1500, sd_masa_rel_pct=0, sd_pureza_pts=0, sd_pureza_producto_pts=0.4),
        pureza_real_pct=98.0,
    )
    assert inc.pureza_producto_pct.media == pytest.approx(98.0, abs=0.1)
    assert inc.pureza_producto_pct.sd == pytest.approx(0.4, abs=0.1)
    # el mínimo orientativo es 98,5: con media 98,0 y desvío 0,4 casi nunca se cumple
    assert inc.prob_cumple_pureza < 0.2


def test_probabilidad_de_cumplir_es_coherente(mezcla_ejemplo, catalogo, reaccion):
    inc = _analizar(mezcla_ejemplo, catalogo, reaccion)
    assert 0.0 <= inc.prob_cumple_pureza <= 1.0


def test_sin_reactivos_no_hay_incertidumbre(catalogo, reaccion):
    from app.models.schemas import ComponenteEntrada

    ent = _entrada([ComponenteEntrada(id="ibb", gramos=100, pureza=98)])
    assert incertidumbre.analizar(ent, catalogo, reaccion, ParametrosIncertidumbre(n=300)) is None


def test_rendimiento_medido_a_partir_de_replicas():
    ent = SimulacionEntrada(componentes=[], rendimiento_replicas_pct=[70, 80])
    media, sd = incertidumbre.rendimiento_medido(ent)
    assert media == 75 and sd == pytest.approx(statistics.stdev([70, 80]))
    assert incertidumbre.rendimiento_medido(SimulacionEntrada(componentes=[], rendimiento_real_pct=60)) == (60, None)


def test_replicas_y_rendimiento_a_la_vez_es_un_error():
    with pytest.raises(ValueError, match="no los dos"):
        SimulacionEntrada(componentes=[], rendimiento_real_pct=60, rendimiento_replicas_pct=[60, 61])
    with pytest.raises(ValueError):
        SimulacionEntrada(componentes=[], rendimiento_replicas_pct=[60, 160])
