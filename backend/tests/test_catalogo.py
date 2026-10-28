"""Integridad del catálogo y de las reacciones: se comprueban solos, sin confiar en lo tipeado."""
import json
from pathlib import Path

import pytest

from app.core import formulas, reacciones
from app.core.simulador import cargar_reacciones
from app.db import database, seed
from app.models.schemas import Compuesto

DATA = Path(__file__).resolve().parents[1] / "app" / "data"


@pytest.fixture(scope="module")
def crudos():
    with open(DATA / "compuestos.json", encoding="utf-8") as f:
        return json.load(f)


def test_ids_y_cas_unicos(crudos):
    ids = [c["id"] for c in crudos]
    cas = [c["cas"] for c in crudos]
    assert len(ids) == len(set(ids))
    assert len(cas) == len(set(cas))


def test_formato_del_cas(crudos):
    """El último dígito de un CAS es de control: se verifica el de cada compuesto."""
    for c in crudos:
        cuerpo, control = c["cas"].rsplit("-", 1)
        digitos = cuerpo.replace("-", "")
        suma = sum(int(d) * (i + 1) for i, d in enumerate(reversed(digitos)))
        assert suma % 10 == int(control), f"{c['id']}: CAS {c['cas']} inválido"


def test_peso_molecular_coincide_con_la_formula(crudos):
    for c in crudos:
        if c["pm_aplicable"]:
            assert c["pm"] == pytest.approx(formulas.peso_molecular(c["formula"]), abs=0.006), c["id"]
        else:
            assert c["pm"] is None, c["id"]


def test_categorias_validas(crudos):
    with open(DATA / "categorias.json", encoding="utf-8") as f:
        cats = set(json.load(f))
    assert {c["categoria"] for c in crudos} <= cats


def test_los_del_prototipo_siguen_ahi(crudos):
    por_id = {c["id"]: c for c in crudos}
    esperados = {"ibb": 134.22, "aa": 102.09, "h2": 2.02, "co": 28.01}
    for id_, pm in esperados.items():
        assert por_id[id_]["pm"] == pytest.approx(pm, abs=0.01)
    assert por_id["cat"]["pm"] == pytest.approx(133.34, abs=0.02)
    assert por_id["ibuprofeno"]["pm"] == pytest.approx(206.28, abs=0.01)


def test_sustancias_fiscalizadas_estan_marcadas(crudos):
    """Las comprobadas en fuentes (RENPRE) deben llevar la marca y el texto de regulación."""
    por_id = {c["id"]: c for c in crudos}
    for id_ in ("aa", "acetona", "hcl", "h2so4", "tolueno", "kmno4", "naoh", "nh3", "ciclohexano"):
        assert por_id[id_]["acceso"] == "controlado", id_
        assert "RENPRE" in por_id[id_]["regulacion"], id_
    assert por_id["agua"]["acceso"] == "libre" and por_id["agua"]["regulacion"] is None


def test_no_hay_material_radiactivo_como_sustancia(crudos):
    with open(DATA / "elementos.json", encoding="utf-8") as f:
        radiactivos = {e["simbolo"] for e in json.load(f) if e["radiactivo"]}
    for c in crudos:
        assert c["formula"] not in radiactivos, c["id"]


def test_todas_las_reacciones_son_validas_y_estan_balanceadas(crudos):
    catalogo = {c["id"]: Compuesto.model_validate({**c, "pm": c["pm"] or 0.0}) for c in crudos}
    todas = cargar_reacciones()
    assert len(todas) >= 10
    for r in todas.values():
        reacciones.validar(r, catalogo)  # lanza si algo no existe o no conserva los átomos


def test_reaccion_desbalanceada_se_rechaza(crudos):
    catalogo = {c["id"]: Compuesto.model_validate({**c, "pm": c["pm"] or 0.0}) for c in crudos}
    mala = cargar_reacciones()["neutralizacion-hcl-naoh"].model_copy(deep=True)
    mala.productos[1].coef = 2
    with pytest.raises(reacciones.ReaccionInvalida, match="no conserva"):
        reacciones.validar(mala, catalogo)


def test_la_base_refleja_los_json():
    database.init_db()
    seed.cargar_datos()
    assert len(database.listar_compuestos()) == len(seed.leer_compuestos())
    assert len(database.listar_elementos()) == 118
    de_db = {r.id: r for r in database.listar_reacciones()}
    de_json = cargar_reacciones()
    assert de_db.keys() == de_json.keys()
    for id_, r in de_json.items():
        assert de_db[id_] == r, id_


def test_migracion_desde_el_esquema_viejo(tmp_path, monkeypatch):
    """Una base creada por la versión anterior se reconstruye sola al arrancar."""
    import sqlite3

    ruta = tmp_path / "vieja.db"
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE compuestos (id TEXT PRIMARY KEY, nombre TEXT, rol TEXT, tipo TEXT, fase TEXT, pm REAL, coef INTEGER, smiles TEXT, formula TEXT, fuente TEXT)")
    con.execute("INSERT INTO compuestos VALUES ('ibb','Isobutilbenceno','Materia prima','reactivo','líquido',134.22,1,NULL,'C10H14','')")
    con.commit()
    con.close()
    monkeypatch.setenv("SIM_DB_PATH", str(ruta))
    database.init_db()
    seed.cargar_datos()
    c = database.obtener_compuesto("ibb")
    assert c is not None and c.cas == "538-93-2"
