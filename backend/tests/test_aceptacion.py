"""Panel de aceptación de ensayos: contadores por estado, cola ordenada por antigüedad y datos de la última decisión."""
import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.main import app

CLAVE = "Clave-Segura-123"
SECRETO = "x" * 40
EJEMPLO = [
    {"id": "ibb", "gramos": 134, "pureza": 99},
    {"id": "aa", "gramos": 102, "pureza": 98},
    {"id": "cat", "gramos": 20, "pureza": 97},
    {"id": "h2", "gramos": 2, "pureza": 99},
    {"id": "co", "gramos": 28, "pureza": 98},
    {"id": "exc", "gramos": 30, "pureza": 99},
]


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("SIM_AUTH", "on")
    monkeypatch.setenv("SIM_SECRET", SECRETO)
    monkeypatch.setenv("SIM_ADMIN_EMAIL", "admin@laboratorio.com")
    monkeypatch.setenv("SIM_ADMIN_CLAVE", CLAVE)
    monkeypatch.setenv("SIM_DATABASE_URL", f"sqlite:///{tmp_path / 'datos.db'}")
    auth.LIMITE_LOGIN.reiniciar()
    with TestClient(app) as c:
        yield c


def entrar(c, email="admin@laboratorio.com"):
    r = c.post("/api/auth/login", json={"email": email, "clave": CLAVE})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def crear(c, admin, email, rol):
    r = c.post("/api/usuarios", headers=admin, json={"email": email, "nombre": email, "rol": rol, "clave": CLAVE})
    assert r.status_code == 201, r.text


@pytest.fixture
def equipo(servidor):
    """Una analista y dos personas de calidad (quien revisa y quien aprueba pueden ser distintas)."""
    admin = entrar(servidor)
    for email, rol in (("ana@l.com", "analista"), ("cal@l.com", "calidad"), ("rev@l.com", "calidad"), ("lee@l.com", "lectura")):
        crear(servidor, admin, email, rol)
    return {n: entrar(servidor, f"{n}@l.com") for n in ("ana", "cal", "rev", "lee")}


def ensayo(c, h, lote="L"):
    r = c.post("/api/ensayos", headers=h, json={"componentes": EJEMPLO, "lote": lote})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def evento(c, h, ensayo_id, tipo, comentario=""):
    return c.post(f"/api/ensayos/{ensayo_id}/eventos", headers=h, json={"tipo": tipo, "comentario": comentario})


def test_el_conteo_separa_estados_y_reemplazados(servidor, equipo):
    ana, cal, rev = equipo["ana"], equipo["cal"], equipo["rev"]
    vacio = servidor.get("/api/ensayos/conteo", headers=cal).json()
    assert vacio == {"registrado": 0, "revisado": 0, "aprobado": 0, "rechazado": 0, "reemplazados": 0, "total": 0}

    for lote in ("A", "B", "C", "D"):  # 1..4
        ensayo(servidor, ana, lote)
    assert evento(servidor, cal, 1, "revisado", "ok").status_code == 201
    assert evento(servidor, rev, 1, "aprobado", "conforme").status_code == 201
    assert evento(servidor, cal, 2, "rechazado", "pureza fuera de límite").status_code == 201
    assert evento(servidor, cal, 3, "revisado").status_code == 201
    assert servidor.post("/api/ensayos/4/corregir", headers=ana, json={"componentes": EJEMPLO, "notas": "balanza"}).status_code == 201  # 5 reemplaza al 4

    c = servidor.get("/api/ensayos/conteo", headers=cal).json()
    # 1 aprobado, 2 rechazado, 3 revisado, 4 reemplazado, 5 registrado
    assert c == {"registrado": 1, "revisado": 1, "aprobado": 1, "rechazado": 1, "reemplazados": 1, "total": 5}
    # los contadores coinciden con lo que devuelve el listado de vigentes
    for estado in ("registrado", "revisado", "aprobado", "rechazado"):
        lista = servidor.get("/api/ensayos", headers=cal, params={"estado": estado, "solo_vigentes": True})
        assert int(lista.headers["X-Total-Count"]) == c[estado], estado


def test_el_conteo_lo_ve_cualquiera_con_sesion_y_no_choca_con_el_id(servidor, equipo):
    assert servidor.get("/api/ensayos/conteo", headers=equipo["lee"]).status_code == 200
    assert servidor.get("/api/ensayos/conteo").status_code == 401
    assert servidor.get("/api/ensayos/99", headers=equipo["lee"]).status_code == 404  # la ruta fija no tapa a /ensayos/{id}


def test_la_cola_se_ordena_por_antiguedad(servidor, equipo):
    for lote in ("A", "B", "C"):
        ensayo(servidor, equipo["ana"], lote)
    cal = equipo["cal"]
    nuevos_primero = [e["id"] for e in servidor.get("/api/ensayos", headers=cal).json()]
    viejos_primero = [e["id"] for e in servidor.get("/api/ensayos", headers=cal, params={"orden": "antiguos"}).json()]
    assert nuevos_primero == [3, 2, 1] and viejos_primero == [1, 2, 3]
    # el orden se aplica antes de paginar
    pagina = servidor.get("/api/ensayos", headers=cal, params={"orden": "antiguos", "limit": 2, "offset": 1}).json()
    assert [e["id"] for e in pagina] == [2, 3]
    # también con filtro por estado
    cola = servidor.get("/api/ensayos", headers=cal, params={"estado": "registrado", "solo_vigentes": True, "orden": "antiguos"}).json()
    assert [e["id"] for e in cola] == [1, 2, 3]
    assert servidor.get("/api/ensayos", headers=cal, params={"orden": "cualquiera"}).status_code == 422


def test_el_resumen_trae_la_ultima_decision_y_los_comentarios(servidor, equipo):
    ana, cal, rev = equipo["ana"], equipo["cal"], equipo["rev"]
    ensayo(servidor, ana)
    sin = servidor.get("/api/ensayos/1", headers=cal).json()
    assert sin["revision_por"] is None and sin["revision_en"] is None and sin["revision_comentario"] is None and sin["n_comentarios"] == 0

    assert evento(servidor, ana, 1, "comentario", "pesada con balanza B").status_code == 201
    assert evento(servidor, cal, 1, "revisado", "datos de pesada verificados").status_code == 201
    parcial = servidor.get("/api/ensayos", headers=cal).json()[0]
    assert parcial["estado"] == "revisado" and parcial["revision_por"] == "cal@l.com" and parcial["revision_comentario"] == "datos de pesada verificados"
    assert parcial["n_comentarios"] == 1

    assert evento(servidor, rev, 1, "aprobado").status_code == 201  # aprobar sin comentario sigue siendo válido
    final = servidor.get("/api/ensayos/1", headers=cal).json()
    assert final["estado"] == "aprobado" and final["revision_por"] == "rev@l.com" and final["revision_en"]
    assert final["revision_comentario"] is None  # la última decisión no tenía comentario: no se arrastra el de la anterior
    assert final["n_comentarios"] == 1
    assert [e["tipo"] for e in final["eventos"]] == ["comentario", "revisado", "aprobado"]
    # la comparación sigue armándose con los resúmenes ampliados
    ensayo(servidor, ana)
    assert servidor.get("/api/ensayos/comparar", headers=cal, params={"ids": "1,2"}).status_code == 200
    # y la cadena de auditoría no se enteró de nada raro: no hay columnas ni escrituras nuevas
    assert servidor.get("/api/auditoria/verificar", headers=cal).json()["ok"]
