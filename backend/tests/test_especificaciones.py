"""Especificación de varios parámetros: lo que no tiene límite o no se midió NO se da por cumplido."""
import pytest

from app.core import especificaciones as esp
from app.core.simulador import simular
from app.models.schemas import Especificacion


def _spec(id_, minimo=None, maximo=None, modelado=False, producto="ibuprofeno"):
    return Especificacion(id=id_, producto=producto, parametro=id_, minimo=minimo, maximo=maximo, unidad="%", modelado=modelado)


SPECS = [
    _spec("pureza", minimo=98.5, modelado=True),
    _spec("perdida-secado", maximo=0.5),
    _spec("relacionadas", maximo=1.0),
    _spec("sin-limite"),
]


def test_cumple_solo_si_todo_cumple():
    specs = [s for s in SPECS if s.id != "sin-limite"]
    ev, global_, _ = esp.evaluar(specs, "ibuprofeno", 99.0, "experimental", {"perdida-secado": 0.3, "relacionadas": 0.8})
    assert global_ == "cumple" and [x.estado for x in ev] == ["cumple"] * 3
    assert ev[0].origen == "medido" and ev[1].origen == "medido"


def test_un_parametro_fuera_de_limite_es_no_cumple():
    specs = [s for s in SPECS if s.id != "sin-limite"]
    ev, global_, _ = esp.evaluar(specs, "ibuprofeno", 99.0, "modelo", {"perdida-secado": 0.9, "relacionadas": 0.8})
    assert global_ == "no_cumple"
    assert next(x for x in ev if x.id == "perdida-secado").estado == "no_cumple"
    assert next(x for x in ev if x.id == "pureza").origen == "modelo"


def test_sin_medicion_es_incompleto_no_cumple():
    specs = [s for s in SPECS if s.id != "sin-limite"]
    ev, global_, _ = esp.evaluar(specs, "ibuprofeno", 99.0, "modelo", {"perdida-secado": 0.3})
    assert global_ == "incompleto"
    assert next(x for x in ev if x.id == "relacionadas").estado == "sin_dato"


def test_sin_limite_cargado_es_incompleto_aunque_haya_medicion():
    ev, global_, _ = esp.evaluar(SPECS, "ibuprofeno", 99.0, "modelo", {"perdida-secado": 0.3, "relacionadas": 0.8, "sin-limite": 5.0})
    assert global_ == "incompleto"
    x = next(x for x in ev if x.id == "sin-limite")
    assert x.estado == "sin_limite" and x.valor == 5.0


def test_limites_incluyen_el_borde():
    ev, g, _ = esp.evaluar([_spec("p", minimo=98.5, modelado=True)], "ibuprofeno", 98.5, "modelo", {})
    assert g == "cumple"


def test_medicion_de_id_inexistente_es_error():
    with pytest.raises(ValueError, match="no existe"):
        esp.evaluar(SPECS, "ibuprofeno", 99, "modelo", {"perdida-de-secado": 0.1})  # typo a propósito


def test_medicion_de_otro_producto_se_ignora_con_aviso():
    specs = SPECS + [_spec("aspirina-x", maximo=1, producto="aspirina")]
    _, _, avisos = esp.evaluar(specs, "ibuprofeno", 99, "modelo", {"aspirina-x": 0.1})
    assert avisos and "otro producto" in avisos[0]


def test_producto_sin_especificaciones():
    ev, g, _ = esp.evaluar(SPECS, "paracetamol", 99, "modelo", {})
    assert ev == [] and g == "sin_especificaciones"


# ---------- integrado en la simulación con las especificaciones reales cargadas ----------
def test_el_ibuprofeno_del_catalogo_queda_incompleto_hasta_cargar_los_limites(mezcla_ejemplo, catalogo, reaccion):
    import json
    from pathlib import Path

    datos = Path(__file__).resolve().parents[1] / "app" / "data" / "especificaciones.json"
    specs = [Especificacion.model_validate(x) for x in json.load(open(datos, encoding="utf-8"))]
    out = simular(mezcla_ejemplo, catalogo, reaccion, especificaciones=specs)
    r = out.resultado
    assert len(r.especificaciones) >= 5
    assert r.cumplimiento_especificaciones in ("incompleto", "no_cumple")
    assert any(x.estado == "sin_limite" for x in r.especificaciones)
    assert any(a.tipo in ("info", "bad") for a in out.alertas)


def test_pureza_medida_pasa_a_ser_dato_medido(mezcla_ejemplo, catalogo, reaccion):
    specs = [_spec("pureza", minimo=98.5, modelado=True)]
    modelo = simular(mezcla_ejemplo, catalogo, reaccion, especificaciones=specs).resultado
    medido = simular(mezcla_ejemplo, catalogo, reaccion, pureza_real_pct=99.4, especificaciones=specs).resultado
    assert modelo.origen == "estimacion" and modelo.cumplimiento_especificaciones == "no_cumple"  # 97,6 % < 98,5
    assert medido.origen == "mixto" and medido.pureza_origen == "experimental"
    assert medido.pureza_producto_pct == 99.4 and medido.cumple_pureza
    assert medido.cumplimiento_especificaciones == "cumple"
    ambos = simular(mezcla_ejemplo, catalogo, reaccion, rendimiento_real_pct=80, pureza_real_pct=99.4).resultado
    assert ambos.origen == "medido"
