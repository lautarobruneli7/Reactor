"""Carga de datos desde los JSON de app/data a SQLite.

Antes de guardar valida todo (esquemas, ids, balance de cada reacción): si un
dato está mal, el programa no arranca en lugar de simular con datos dudosos.

Se puede correr a mano:  python -m app.db.seed
"""
import json
from pathlib import Path

from app.core import reacciones as validador
from app.db.database import get_conn, init_db, normalizar
from app.models.schemas import Compuesto, Elemento, Especificacion, Reaccion

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _leer(nombre: str):
    with open(DATA_DIR / nombre, encoding="utf-8") as f:
        return json.load(f)


def cargar_categorias() -> list[str]:
    return _leer("categorias.json")


def leer_compuestos() -> list[Compuesto]:
    return [Compuesto.model_validate({**x, "pm": x.get("pm") or 0.0}) for x in _leer("compuestos.json")]


def leer_reacciones() -> list[Reaccion]:
    return [Reaccion.model_validate(x) for x in _leer("reacciones.json")]


def cargar_datos() -> None:
    elementos = [Elemento.model_validate(x) for x in _leer("elementos.json")]
    compuestos = leer_compuestos()
    reacciones = leer_reacciones()
    specs = [Especificacion.model_validate(x) for x in _leer("especificaciones.json")]

    catalogo = {c.id: c for c in compuestos}
    if len(catalogo) != len(compuestos):
        raise ValueError("Hay ids de compuestos repetidos en compuestos.json")
    categorias = set(cargar_categorias())
    for c in compuestos:
        if c.categoria not in categorias:
            raise ValueError(f"{c.id}: categoría desconocida {c.categoria!r}")
    for r in reacciones:
        validador.validar(r, catalogo)

    with get_conn() as c:
        # la base es una copia de los JSON: se rehace completa para que nunca queden datos viejos
        for tabla in ("reaccion_participantes", "reacciones", "compuestos", "elementos", "especificaciones"):
            c.execute(f"DELETE FROM {tabla}")
        for e in elementos:
            c.execute(
                "INSERT INTO elementos (numero, simbolo, nombre, nombre_en, masa_atomica, grupo, periodo, categoria, fase_25c, radiactivo, fuente) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (e.numero, e.simbolo, e.nombre, e.nombre_en, e.masa_atomica, e.grupo, e.periodo,
                 e.categoria, e.fase_25c, int(e.radiactivo), e.fuente),
            )
        for x in compuestos:
            busqueda = normalizar(" ".join([x.nombre, x.formula or "", x.formula_hill or "", x.cas or "", x.id, *x.sinonimos]))
            c.execute(
                "INSERT INTO compuestos (id, nombre, rol, tipo, categoria, fase, formula, formula_hill, cas, pm, pm_aplicable, "
                "smiles, inchikey, pubchem_cid, tm_c, tb_c, sinonimos, nota, acceso, regulacion, verificado, fuente, busqueda) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (x.id, x.nombre, x.rol, x.tipo, x.categoria, x.fase, x.formula, x.formula_hill, x.cas, x.pm,
                 int(x.pm_aplicable), x.smiles, x.inchikey, x.pubchem_cid, x.tm_c, x.tb_c,
                 json.dumps(x.sinonimos, ensure_ascii=False), x.nota, x.acceso, x.regulacion,
                 int(x.verificado), x.fuente, busqueda),
            )
        for r in reacciones:
            c.execute(
                "INSERT INTO reacciones (id, nombre, descripcion, categoria, catalizador, excipiente, parametros, fuente, estado_validacion) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r.id, r.nombre, r.descripcion, r.categoria, r.catalizador, r.excipiente,
                 json.dumps(r.parametros.model_dump(exclude_defaults=True), ensure_ascii=False), r.fuente, r.estado_validacion),
            )
            for i, p in enumerate(r.reactivos):
                c.execute("INSERT INTO reaccion_participantes VALUES (?, ?, 'reactivo', ?, 0, ?)", (r.id, p.id, p.coef, i))
            for i, p in enumerate(r.productos):
                c.execute("INSERT INTO reaccion_participantes VALUES (?, ?, 'producto', ?, ?, ?)", (r.id, p.id, p.coef, int(p.principal), i))
        for s in specs:
            c.execute(
                "INSERT INTO especificaciones (id, producto, parametro, minimo, maximo, unidad, fuente, estado, modelado, tipo, farmacopea) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (s.id, s.producto, s.parametro, s.minimo, s.maximo, s.unidad, s.fuente, s.estado, int(s.modelado), s.tipo, s.farmacopea),
            )


if __name__ == "__main__":
    init_db()
    cargar_datos()
    print("Datos cargados.")
