"""API: unidades, concentraciones, incertidumbre y especificaciones."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


EJEMPLO = [
    {"id": "ibb", "gramos": 134, "pureza": 99},
    {"id": "aa", "gramos": 102, "pureza": 98},
    {"id": "cat", "gramos": 20, "pureza": 97},
    {"id": "h2", "gramos": 2, "pureza": 99},
    {"id": "co", "gramos": 28, "pureza": 98},
    {"id": "exc", "gramos": 30, "pureza": 99},
]


def test_convertir_unidades(client):
    r = client.post("/api/unidades/convertir", json={"compuesto_id": "naoh", "cantidad": 0.5, "unidad": "mol", "a_unidad": "g"})
    assert r.status_code == 200
    assert r.json()["valor"] == pytest.approx(20.0, abs=0.01)
    r = client.post("/api/unidades/convertir", json={"compuesto_id": "etanol", "cantidad": 100, "unidad": "mL", "a_unidad": "mol"})
    assert r.status_code == 200 and r.json()["valor"] == pytest.approx(100 * 0.79 / 46.07, rel=0.01)


def test_convertir_sin_densidad_es_422_y_explica(client):
    r = client.post("/api/unidades/convertir", json={"compuesto_id": "ibb", "cantidad": 10, "unidad": "mL", "a_unidad": "g"})
    assert r.status_code == 422 and "densidad" in r.json()["detail"]
    assert client.post("/api/unidades/convertir", json={"compuesto_id": "zzz", "cantidad": 1, "unidad": "g", "a_unidad": "mol"}).status_code == 404


def test_convertir_solucion(client):
    r = client.post("/api/unidades/convertir", json={
        "compuesto_id": "hcl", "cantidad": 100, "unidad": "g", "a_unidad": "mol",
        "concentracion": {"tipo": "p/p", "valor": 37},
    })
    assert r.status_code == 200 and r.json()["valor"] == pytest.approx(37 / 36.46, rel=0.01)


def test_convertir_concentracion(client):
    r = client.post("/api/soluciones/convertir", json={
        "concentracion": {"tipo": "p/p", "valor": 37}, "compuesto_id": "hcl", "densidad_g_ml": 1.18,
    })
    assert r.status_code == 200
    assert r.json()["molar"] == pytest.approx(0.37 * 1180 / 36.46, rel=0.01)
    por_formula = client.post("/api/soluciones/convertir", json={
        "concentracion": {"tipo": "molar", "valor": 1.0}, "formula": "NaCl", "densidad_g_ml": 1.04,
    })
    assert por_formula.status_code == 200 and por_formula.json()["p_p_pct"] == pytest.approx(58.44 / 1040 * 100, rel=0.01)
    assert client.post("/api/soluciones/convertir", json={"concentracion": {"tipo": "molar", "valor": 1.0}, "formula": "NaCl"}).status_code == 422
    assert client.post("/api/soluciones/convertir", json={"concentracion": {"tipo": "p/p", "valor": 5}}).status_code == 422


def test_densidad_del_catalogo(client):
    r = client.get("/api/compuestos/etanol/densidad")
    assert r.status_code == 200
    d = r.json()
    assert d["densidad_g_ml"] == pytest.approx(0.79, abs=0.01) and d["temperatura_c"] == 20 and d["fuente"] and d["verificacion_cruzada"]
    assert client.get("/api/compuestos/ibb/densidad").status_code == 404
    assert client.get("/api/compuestos/zzz/densidad").status_code == 404


def test_simulacion_con_unidades_y_solucion(client):
    r = client.post("/api/simulacion", json={
        "reaccion_id": "neutralizacion-hcl-naoh",
        "componentes": [
            {"id": "hcl", "cantidad": 98.54, "unidad": "g", "pureza": 100, "concentracion": {"tipo": "p/p", "valor": 37}},
            {"id": "naoh", "cantidad": 1, "unidad": "mol", "pureza": 100},
        ],
    })
    assert r.status_code == 200
    res = r.json()["resultado"]
    assert res["gramos_teoricos"] == pytest.approx(58.44, abs=0.1)
    assert res["origen"] == "estimacion" and res["estado_validacion"]


def test_cantidad_y_gramos_a_la_vez_es_error(client):
    r = client.post("/api/simulacion", json={"componentes": [{"id": "ibb", "gramos": 1, "cantidad": 1, "unidad": "g", "pureza": 99}]})
    assert r.status_code == 422
    assert client.post("/api/simulacion", json={"componentes": [{"id": "ibb", "pureza": 99}]}).status_code == 422


def test_falta_de_densidad_en_la_simulacion_es_422(client):
    r = client.post("/api/simulacion", json={
        "reaccion_id": "neutralizacion-hcl-naoh",
        "componentes": [{"id": "hcl", "cantidad": 10, "unidad": "mL", "pureza": 100, "concentracion": {"tipo": "p/p", "valor": 37}},
                        {"id": "naoh", "gramos": 10, "pureza": 100}],
    })
    assert r.status_code == 422 and "densidad" in r.json()["detail"]


def test_simulacion_con_incertidumbre(client):
    r = client.post("/api/simulacion", json={"componentes": EJEMPLO, "incertidumbre": {"n": 300, "semilla": 1}})
    assert r.status_code == 200
    inc = r.json()["resultado"]["incertidumbre"]
    assert inc["n"] == 300 and inc["rendimiento_pct"]["p5"] <= inc["rendimiento_pct"]["p95"]
    assert inc["incluye_incertidumbre_del_modelo"] is False and inc["notas"]
    assert client.post("/api/simulacion", json={"componentes": EJEMPLO, "incertidumbre": {"n": 5}}).status_code == 422


def test_simulacion_con_replicas_y_pureza_medida(client):
    r = client.post("/api/simulacion", json={
        "componentes": EJEMPLO, "rendimiento_replicas_pct": [80, 82, 78], "pureza_real_pct": 99.1,
        "incertidumbre": {"n": 300, "sd_pureza_producto_pts": 0.2},
    })
    assert r.status_code == 200
    res = r.json()["resultado"]
    assert res["rendimiento_pct"] == 80 and res["rendimiento_origen"] == "experimental"
    assert res["pureza_origen"] == "experimental" and res["origen"] == "medido"
    assert res["incertidumbre"]["incluye_incertidumbre_del_modelo"] is True


def test_especificaciones_con_mediciones(client):
    ok = client.post("/api/simulacion", json={"componentes": EJEMPLO, "mediciones": {"ibuprofeno-perdida-secado": 0.3}})
    assert ok.status_code == 200
    ev = {x["id"]: x for x in ok.json()["resultado"]["especificaciones"]}
    assert ev["ibuprofeno-perdida-secado"]["valor"] == 0.3 and ev["ibuprofeno-perdida-secado"]["estado"] == "sin_limite"
    assert ok.json()["resultado"]["cumplimiento_especificaciones"] != "cumple"
    malo = client.post("/api/simulacion", json={"componentes": EJEMPLO, "mediciones": {"no-existe": 1}})
    assert malo.status_code == 422 and "no existe" in malo.json()["detail"]


def test_especificaciones_listadas_con_los_campos_nuevos(client):
    specs = client.get("/api/especificaciones").json()
    por_id = {s["id"]: s for s in specs}
    assert por_id["ibuprofeno-pureza"]["modelado"] is True and por_id["ibuprofeno-pureza"]["minimo"] == 98.5
    assert por_id["ibuprofeno-perdida-secado"]["minimo"] is None and por_id["ibuprofeno-perdida-secado"]["maximo"] is None
