"""Contraseñas, tokens, roles y el flujo de revisión con varias personas."""
import time

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


# ---------- piezas ----------
def test_las_claves_se_guardan_con_sal_y_se_verifican():
    h1, h2 = auth.hash_clave(CLAVE), auth.hash_clave(CLAVE)
    assert h1 != h2 and h1.startswith("scrypt$") and CLAVE not in h1
    assert auth.verificar_clave(CLAVE, h1) and not auth.verificar_clave(CLAVE + "x", h1)
    assert not auth.verificar_clave(CLAVE, "no-es-un-hash") and not auth.verificar_clave(CLAVE, "md5$1$2$3$4$5")


def test_politica_de_claves():
    for mala in ("corta1A", "todominusculas123", "TODOMAYUSCULAS123", "SinNumerosAquiii"):
        with pytest.raises(auth.ClaveDebil):
            auth.validar_clave_nueva(mala)
    auth.validar_clave_nueva(CLAVE)


def test_tokens_firmados_vencen_y_no_se_falsifican():
    t = auth.emitir_token(7, SECRETO, horas=1, ahora=1000)
    assert auth.leer_token(t, SECRETO, ahora=1000 + 3599) == 7
    assert auth.leer_token(t, SECRETO, ahora=1000 + 3601) is None  # venció
    assert auth.leer_token(t, SECRETO + "x", ahora=1000) is None  # otra clave de firma
    payload, firma = t.split(".")
    otro = auth.emitir_token(1, SECRETO, horas=1, ahora=1000).split(".")[0]
    assert auth.leer_token(f"{otro}.{firma}", SECRETO, ahora=1000) is None  # payload cambiado con la firma de otro
    for basura in ("", "a", "a.b", "a.b.c", "....", payload):
        assert auth.leer_token(basura, SECRETO) is None


def test_jerarquia_de_roles():
    assert auth.alcanza("admin", "calidad") and auth.alcanza("calidad", "analista") and auth.alcanza("analista", "lectura")
    assert not auth.alcanza("analista", "calidad") and not auth.alcanza("lectura", "analista") and not auth.alcanza("rol-inventado", "lectura")


def test_limite_de_intentos():
    lim = auth.LimiteDeIntentos(maximo=3, minutos=1)
    for _ in range(2):
        lim.fallo("a@b.c", ahora=0)
    assert lim.bloqueado("a@b.c", ahora=1) == 0
    lim.fallo("a@b.c", ahora=2)
    assert 0 < lim.bloqueado("a@b.c", ahora=3) <= 60
    assert lim.bloqueado("otro@b.c", ahora=3) == 0
    assert lim.bloqueado("a@b.c", ahora=2 + 61) == 0  # pasó el castigo
    lim.fallo("z@b.c", ahora=0)
    lim.acierto("z@b.c")
    assert lim._fallos.get("z@b.c") is None


# ---------- API con login ----------
@pytest.fixture
def servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("SIM_AUTH", "on")
    monkeypatch.setenv("SIM_SECRET", SECRETO)
    monkeypatch.setenv("SIM_ADMIN_EMAIL", "Admin@Laboratorio.com")
    monkeypatch.setenv("SIM_ADMIN_CLAVE", CLAVE)
    monkeypatch.setenv("SIM_DATABASE_URL", f"sqlite:///{tmp_path / 'datos.db'}")
    auth.LIMITE_LOGIN.reiniciar()
    with TestClient(app) as c:
        yield c


def entrar(c, email="admin@laboratorio.com", clave=CLAVE):
    r = c.post("/api/auth/login", json={"email": email, "clave": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def crear(c, admin, email, rol, nombre=None):
    r = c.post("/api/usuarios", headers=admin, json={"email": email, "nombre": nombre or email, "rol": rol, "clave": CLAVE})
    assert r.status_code == 201, r.text
    return r.json()


def test_sin_sesion_no_se_puede_nada_salvo_ver_el_sistema(servidor):
    assert servidor.get("/api/sistema").json()["auth_activa"] is True
    assert servidor.get("/api/salud").status_code == 200
    for ruta in ("/api/ensayos", "/api/auth/yo", "/api/usuarios", "/api/auditoria"):
        r = servidor.get(ruta)
        assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer", ruta
    assert servidor.post("/api/ensayos", json={"componentes": EJEMPLO}).status_code == 401
    assert servidor.get("/api/ensayos", headers={"Authorization": "Bearer basura"}).status_code == 401
    assert servidor.get("/api/ensayos", headers={"Authorization": "Basic xxx"}).status_code == 401


def test_el_admin_inicial_entra_y_queda_en_el_registro(servidor):
    h = entrar(servidor)
    yo = servidor.get("/api/auth/yo", headers=h).json()
    assert yo["rol"] == "admin" and yo["email"] == "admin@laboratorio.com"
    acciones = [r["accion"] for r in servidor.get("/api/auditoria", headers=h).json()]
    assert "sesion.inicio" in acciones and "usuario.crear" in acciones


def test_login_incorrecto_no_distingue_usuario_de_clave_y_se_bloquea(servidor):
    r1 = servidor.post("/api/auth/login", json={"email": "admin@laboratorio.com", "clave": "incorrecta"})
    r2 = servidor.post("/api/auth/login", json={"email": "nadie@laboratorio.com", "clave": CLAVE})
    assert r1.status_code == r2.status_code == 401 and r1.json() == r2.json()
    for _ in range(4):  # con el primero ya son 5 fallos seguidos
        servidor.post("/api/auth/login", json={"email": "admin@laboratorio.com", "clave": "incorrecta"})
    r = servidor.post("/api/auth/login", json={"email": "admin@laboratorio.com", "clave": CLAVE})  # aun con la clave buena
    assert r.status_code == 429 and "Retry-After" in r.headers
    auth.LIMITE_LOGIN.reiniciar()
    assert servidor.post("/api/auth/login", json={"email": "admin@laboratorio.com", "clave": CLAVE}).status_code == 200


def test_roles_cada_uno_hace_lo_suyo(servidor):
    admin = entrar(servidor)
    for email, rol in (("lee@l.com", "lectura"), ("ana@l.com", "analista"), ("cal@l.com", "calidad")):
        crear(servidor, admin, email, rol)
    lee, ana, cal = entrar(servidor, "lee@l.com"), entrar(servidor, "ana@l.com"), entrar(servidor, "cal@l.com")
    cuerpo = {"componentes": EJEMPLO, "lote": "L1"}
    assert servidor.post("/api/ensayos", headers=lee, json=cuerpo).status_code == 403
    assert servidor.get("/api/ensayos", headers=lee).status_code == 200
    assert servidor.post("/api/ensayos", headers=ana, json=cuerpo).status_code == 201
    assert servidor.get("/api/auditoria", headers=ana).status_code == 403
    assert servidor.get("/api/auditoria/verificar", headers=ana).status_code == 403
    assert servidor.get("/api/auditoria/verificar", headers=cal).status_code == 200
    assert servidor.get("/api/usuarios", headers=cal).status_code == 403
    assert servidor.post("/api/usuarios", headers=ana, json={"email": "x@l.com", "nombre": "X", "rol": "lectura", "clave": CLAVE}).status_code == 403
    # el analista solo corrige lo suyo; calidad puede corregir lo de cualquiera
    otra = crear(servidor, admin, "bea@l.com", "analista")
    bea = entrar(servidor, "bea@l.com")
    assert servidor.post("/api/ensayos/1/corregir", headers=bea, json=cuerpo).status_code == 403
    assert otra["rol"] == "analista"
    assert servidor.post("/api/ensayos/1/corregir", headers=cal, json=cuerpo).status_code == 201


def test_flujo_de_revision_y_aprobacion(servidor):
    admin = entrar(servidor)
    crear(servidor, admin, "ana@l.com", "analista")
    crear(servidor, admin, "cal@l.com", "calidad")
    crear(servidor, admin, "rev@l.com", "calidad")
    ana, cal, rev = entrar(servidor, "ana@l.com"), entrar(servidor, "cal@l.com"), entrar(servidor, "rev@l.com")
    assert servidor.post("/api/ensayos", headers=ana, json={"componentes": EJEMPLO}).status_code == 201
    ev = lambda h, tipo, com="": servidor.post("/api/ensayos/1/eventos", headers=h, json={"tipo": tipo, "comentario": com})  # noqa: E731
    assert ev(ana, "revisado").status_code == 403           # el analista no revisa
    assert ev(cal, "aprobado").status_code == 409           # no se aprueba sin revisar antes
    assert ev(cal, "rechazado").status_code == 422          # rechazar exige el motivo
    assert ev(cal, "revisado").json()["estado"] == "revisado"
    assert ev(cal, "revisado").status_code == 409           # ya está revisado
    r = ev(rev, "aprobado", "conforme")
    assert r.status_code == 201 and r.json()["estado"] == "aprobado"
    assert [e["tipo"] for e in r.json()["eventos"]] == ["revisado", "aprobado"]
    assert ev(cal, "rechazado", "tarde").status_code == 409  # un aprobado no vuelve atrás: se corrige con otro ensayo
    assert [e["id"] for e in servidor.get("/api/ensayos", headers=cal, params={"estado": "aprobado"}).json()] == [1]
    # quien hizo el ensayo (aunque sea de calidad) no lo revisa
    assert servidor.post("/api/ensayos", headers=cal, json={"componentes": EJEMPLO}).status_code == 201
    propio = servidor.post("/api/ensayos/2/eventos", headers=cal, json={"tipo": "revisado"})
    assert propio.status_code == 403 and "no puede" in propio.json()["detail"]


def test_un_ensayo_reemplazado_no_se_revisa(servidor):
    admin = entrar(servidor)
    crear(servidor, admin, "ana@l.com", "analista")
    crear(servidor, admin, "cal@l.com", "calidad")
    ana, cal = entrar(servidor, "ana@l.com"), entrar(servidor, "cal@l.com")
    servidor.post("/api/ensayos", headers=ana, json={"componentes": EJEMPLO})
    servidor.post("/api/ensayos/1/corregir", headers=ana, json={"componentes": EJEMPLO, "notas": "corrección"})
    r = servidor.post("/api/ensayos/1/eventos", headers=cal, json={"tipo": "revisado"})
    assert r.status_code == 409 and "reemplazado" in r.json()["detail"]
    assert servidor.post("/api/ensayos/2/eventos", headers=cal, json={"tipo": "revisado"}).status_code == 201


def test_administracion_de_usuarios(servidor):
    admin = entrar(servidor)
    crear(servidor, admin, "ana@l.com", "analista")
    assert servidor.post("/api/usuarios", headers=admin, json={"email": "ANA@l.com", "nombre": "x", "rol": "lectura", "clave": CLAVE}).status_code == 409
    assert servidor.post("/api/usuarios", headers=admin, json={"email": "d@l.com", "nombre": "d", "rol": "lectura", "clave": "debil"}).status_code == 422
    assert servidor.post("/api/usuarios", headers=admin, json={"email": "d@l.com", "nombre": "d", "rol": "inventado", "clave": CLAVE}).status_code == 422
    assert servidor.post("/api/usuarios", headers=admin, json={"email": "no-es-correo", "nombre": "d", "rol": "lectura", "clave": CLAVE}).status_code == 422
    ana = entrar(servidor, "ana@l.com")
    # desactivar: el token que ya tenía deja de servir y no puede volver a entrar
    ana_id = next(u["id"] for u in servidor.get("/api/usuarios", headers=admin).json() if u["email"] == "ana@l.com")
    assert servidor.patch(f"/api/usuarios/{ana_id}", headers=admin, json={"activo": False}).json()["activo"] is False
    assert servidor.get("/api/auth/yo", headers=ana).status_code == 401
    assert servidor.post("/api/auth/login", json={"email": "ana@l.com", "clave": CLAVE}).status_code == 401
    # restablecer clave
    servidor.patch(f"/api/usuarios/{ana_id}", headers=admin, json={"activo": True, "clave": "Otra-Clave-456"})
    assert servidor.post("/api/auth/login", json={"email": "ana@l.com", "clave": CLAVE}).status_code == 401
    assert servidor.post("/api/auth/login", json={"email": "ana@l.com", "clave": "Otra-Clave-456"}).status_code == 200
    assert servidor.patch("/api/usuarios/999", headers=admin, json={"activo": False}).status_code == 404
    assert servidor.patch(f"/api/usuarios/{ana_id}", headers=admin, json={}).status_code == 422
    # nunca se queda sin administrador
    admin_id = next(u["id"] for u in servidor.get("/api/usuarios", headers=admin).json() if u["rol"] == "admin")
    assert servidor.patch(f"/api/usuarios/{admin_id}", headers=admin, json={"rol": "calidad"}).status_code == 409
    assert servidor.patch(f"/api/usuarios/{admin_id}", headers=admin, json={"activo": False}).status_code == 409
    # las claves no quedan en la auditoría
    cuerpo = servidor.get("/api/auditoria", headers=admin, params={"limit": 500}).text
    assert CLAVE not in cuerpo and "Otra-Clave-456" not in cuerpo and "scrypt$" not in cuerpo
    assert servidor.get("/api/auditoria/verificar", headers=admin).json()["ok"]


def test_sin_clave_de_firma_no_arranca(tmp_path, monkeypatch):
    monkeypatch.setenv("SIM_AUTH", "on")
    monkeypatch.setenv("SIM_SECRET", "corta")
    monkeypatch.setenv("SIM_DATABASE_URL", f"sqlite:///{tmp_path / 'datos.db'}")
    with pytest.raises(RuntimeError, match="SIM_SECRET"):
        with TestClient(app):
            pass


def test_token_vencido_por_el_tiempo(servidor, monkeypatch):
    import types

    reloj = types.SimpleNamespace(t=time.time())
    monkeypatch.setattr("app.core.auth.time", types.SimpleNamespace(time=lambda: reloj.t))  # reloj propio solo para el módulo auth
    h = entrar(servidor)
    assert servidor.get("/api/auth/yo", headers=h).status_code == 200
    reloj.t += 7 * 3600  # 7 horas después (el token dura 8)
    assert servidor.get("/api/auth/yo", headers=h).status_code == 200
    reloj.t += 2 * 3600  # 9 horas después
    r = servidor.get("/api/auth/yo", headers=h)
    assert r.status_code == 401 and "venció" in r.json()["detail"]
