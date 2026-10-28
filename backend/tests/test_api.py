import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # el "with" ejecuta el lifespan (crea y llena la base)
        yield c


def _ejemplo():
    return {"componentes": [
        {"id": "ibb", "gramos": 134, "pureza": 99},
        {"id": "aa", "gramos": 102, "pureza": 98},
        {"id": "cat", "gramos": 20, "pureza": 97},
        {"id": "h2", "gramos": 2, "pureza": 99},
        {"id": "co", "gramos": 28, "pureza": 98},
        {"id": "exc", "gramos": 30, "pureza": 99},
    ]}


def test_salud(client):
    r = client.get("/api/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


def test_listar_compuestos(client):
    r = client.get("/api/compuestos")
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()]
    assert ids[:6] == ["ibb", "aa", "cat", "h2", "co", "exc"]  # los del prototipo conservan id y orden
    assert len(ids) > 100
    assert int(r.headers["X-Total-Count"]) == len(ids)


def test_compuesto_inexistente(client):
    assert client.get("/api/compuestos/nada").status_code == 404


def test_especificaciones(client):
    r = client.get("/api/especificaciones")
    assert r.status_code == 200 and len(r.json()) >= 1


def test_reaccion_activa(client):
    r = client.get("/api/reaccion")
    assert r.status_code == 200
    assert r.json()["producto"]["nombre"] == "Ibuprofeno"


def test_simulacion_ejemplo(client):
    r = client.post("/api/simulacion", json=_ejemplo())
    assert r.status_code == 200
    assert r.json()["resultado"]["puntaje"] == 85


def test_simulacion_vacia_no_da_resultado(client):
    r = client.post("/api/simulacion", json={"componentes": []})
    assert r.status_code == 200
    assert r.json()["resultado"] is None


def test_simulacion_compuesto_desconocido(client):
    r = client.post("/api/simulacion", json={"componentes": [{"id": "zzz", "gramos": 1, "pureza": 100}]})
    assert r.status_code == 404


def test_simulacion_valida_rangos(client):
    r = client.post("/api/simulacion", json={"componentes": [{"id": "ibb", "gramos": -5, "pureza": 150}]})
    assert r.status_code == 422


def test_propiedades_con_o_sin_rdkit(client):
    r = client.get("/api/compuestos/ibb/propiedades")
    assert r.status_code in (200, 501)
    if r.status_code == 200:
        assert r.json()["pm"] == pytest.approx(134.22, abs=0.05)


# ---------- catálogo ampliado ----------
def test_busqueda_ignora_acentos_y_mayusculas(client):
    por_acento = {c["id"] for c in client.get("/api/compuestos", params={"q": "ÁCIDO acético"}).json()}
    sin_acento = {c["id"] for c in client.get("/api/compuestos", params={"q": "acido acetico"}).json()}
    assert "acido-acetico" in por_acento and por_acento == sin_acento


def test_busqueda_por_cas_formula_y_sinonimo(client):
    assert [c["id"] for c in client.get("/api/compuestos", params={"q": "15687-27-1"}).json()] == ["ibuprofeno"]
    assert "etanol" in [c["id"] for c in client.get("/api/compuestos", params={"q": "C2H6O"}).json()]
    assert "aspirina" in [c["id"] for c in client.get("/api/compuestos", params={"q": "aspirin"}).json()]


def test_filtros_y_paginacion(client):
    gases = client.get("/api/compuestos", params={"fase": "gas"}).json()
    assert gases and all(c["fase"] == "gas" for c in gases)
    controlados = client.get("/api/compuestos", params={"acceso": "controlado"}).json()
    assert {"aa", "acetona", "hcl"} <= {c["id"] for c in controlados}
    pagina = client.get("/api/compuestos", params={"limit": 5, "offset": 5})
    assert len(pagina.json()) == 5
    assert int(pagina.headers["X-Total-Count"]) > 5


def test_categorias_suman_el_total(client):
    cats = client.get("/api/categorias").json()
    total = len(client.get("/api/compuestos").json())
    assert sum(c["total"] for c in cats) == total
    assert all(c["total"] > 0 for c in cats)


def test_elementos(client):
    els = client.get("/api/elementos").json()
    assert len(els) == 118 and els[0]["simbolo"] == "H" and els[117]["simbolo"] == "Og"
    fe = client.get("/api/elementos/fe").json()
    assert fe["nombre"] == "Hierro" and fe["masa_atomica"] == pytest.approx(55.845)
    assert client.get("/api/elementos/Xx").status_code == 404


def test_peso_molecular_de_cualquier_formula(client):
    r = client.get("/api/formulas/pm", params={"formula": "CuSO4·5H2O"}).json()
    assert r["pm"] == pytest.approx(249.68, abs=0.02)
    assert client.get("/api/formulas/pm", params={"formula": "Xx2"}).status_code == 422


def test_balancear(client):
    r = client.post("/api/estequiometria/balancear", json={"reactivos": ["C3H8", "O2"], "productos": ["CO2", "H2O"]})
    assert r.status_code == 200
    assert [x["coef"] for x in r.json()["reactivos"]] == [1, 5]
    assert [x["coef"] for x in r.json()["productos"]] == [3, 4]
    malo = client.post("/api/estequiometria/balancear", json={"reactivos": ["H2"], "productos": ["NaCl"]})
    assert malo.status_code == 422


def test_reacciones_y_filtro_por_compuesto(client):
    todas = client.get("/api/reacciones").json()
    assert len(todas) >= 10 and all(r["balanceada"] for r in todas)
    con_aa = {r["id"] for r in client.get("/api/reacciones", params={"compuesto": "aa"}).json()}
    assert {"ibuprofeno-simplificada", "aspirina-acetilacion", "paracetamol-acetilacion"} <= con_aa
    assert client.get("/api/reacciones/no-existe").status_code == 404


def test_reaccion_activa_mantiene_el_formato_anterior(client):
    r = client.get("/api/reaccion").json()
    assert r["producto"]["nombre"] == "Ibuprofeno" and r["producto"]["pm"] == pytest.approx(206.28, abs=0.01)
    assert "C13H18O2" in r["ecuacion"]


def test_simulacion_de_otra_reaccion(client):
    r = client.post("/api/simulacion", json={
        "reaccion_id": "neutralizacion-hcl-naoh",
        "componentes": [{"id": "hcl", "gramos": 36.46, "pureza": 100}, {"id": "naoh", "gramos": 40.0, "pureza": 100}],
    })
    assert r.status_code == 200
    res = r.json()["resultado"]
    assert res["gramos_teoricos"] == pytest.approx(58.44, abs=0.02)


def test_simulacion_reaccion_desconocida(client):
    r = client.post("/api/simulacion", json={"reaccion_id": "xxx", "componentes": []})
    assert r.status_code == 404
