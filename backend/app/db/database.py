"""Acceso a SQLite (sqlite3 de la librería estándar).

La base es una copia consultable de los JSON de app/data: se crea sola al
arrancar y se vuelve a llenar completa en cada inicio (no guarda nada que el
usuario haya creado). Para migrar a PostgreSQL más adelante alcanza con
reemplazar este módulo.

Versión del esquema (PRAGMA user_version):
  1 = tablas del prototipo (compuestos simples y especificaciones)
  2 = catálogo ampliado: elementos, compuestos con CAS/categoría/regulación,
      reacciones y sus participantes
  3 = especificaciones de varios parámetros (modelado, tipo, farmacopea)
Al abrir una base de una versión anterior se reconstruye: es seguro porque
todo su contenido sale de los JSON.
"""
import json
import os
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.models.schemas import (
    Compuesto,
    Elemento,
    Especificacion,
    Participante,
    ProductoReaccion,
    Reaccion,
)

VERSION_ESQUEMA = 3


def db_path() -> Path:
    return Path(os.getenv("SIM_DB_PATH", Path(__file__).resolve().parents[2] / "simulador.db"))


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para buscar 'acido' y encontrar 'Ácido'."""
    t = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in t if not unicodedata.combining(ch)).lower().strip()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_TABLAS = ("reaccion_participantes", "reacciones", "compuestos", "elementos", "especificaciones")


def init_db() -> None:
    with get_conn() as c:
        version = c.execute("PRAGMA user_version").fetchone()[0]
        if version < VERSION_ESQUEMA:
            for t in _TABLAS:
                c.execute(f"DROP TABLE IF EXISTS {t}")
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS elementos (
                numero INTEGER PRIMARY KEY,
                simbolo TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                nombre_en TEXT NOT NULL,
                masa_atomica REAL NOT NULL,
                grupo INTEGER,
                periodo INTEGER NOT NULL,
                categoria TEXT NOT NULL,
                fase_25c TEXT,
                radiactivo INTEGER NOT NULL DEFAULT 0,
                fuente TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS compuestos (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL,
                tipo TEXT NOT NULL,
                categoria TEXT NOT NULL,
                fase TEXT NOT NULL,
                formula TEXT,
                formula_hill TEXT,
                cas TEXT UNIQUE,
                pm REAL NOT NULL,
                pm_aplicable INTEGER NOT NULL DEFAULT 1,
                smiles TEXT,
                inchikey TEXT,
                pubchem_cid INTEGER,
                tm_c REAL,
                tb_c REAL,
                sinonimos TEXT NOT NULL DEFAULT '[]',
                nota TEXT NOT NULL DEFAULT '',
                acceso TEXT NOT NULL DEFAULT 'libre',
                regulacion TEXT,
                verificado INTEGER NOT NULL DEFAULT 1,
                fuente TEXT NOT NULL DEFAULT '',
                busqueda TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS ix_compuestos_categoria ON compuestos(categoria);
            CREATE INDEX IF NOT EXISTS ix_compuestos_fase ON compuestos(fase);
            CREATE INDEX IF NOT EXISTS ix_compuestos_acceso ON compuestos(acceso);
            CREATE TABLE IF NOT EXISTS reacciones (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                categoria TEXT NOT NULL DEFAULT '',
                catalizador TEXT REFERENCES compuestos(id),
                excipiente TEXT REFERENCES compuestos(id),
                parametros TEXT NOT NULL DEFAULT '{}',
                fuente TEXT NOT NULL DEFAULT '',
                estado_validacion TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS reaccion_participantes (
                reaccion_id TEXT NOT NULL REFERENCES reacciones(id) ON DELETE CASCADE,
                compuesto_id TEXT NOT NULL REFERENCES compuestos(id),
                lado TEXT NOT NULL CHECK (lado IN ('reactivo', 'producto')),
                coef INTEGER NOT NULL CHECK (coef >= 1),
                principal INTEGER NOT NULL DEFAULT 0,
                orden INTEGER NOT NULL,
                PRIMARY KEY (reaccion_id, compuesto_id, lado)
            );
            CREATE INDEX IF NOT EXISTS ix_part_compuesto ON reaccion_participantes(compuesto_id);
            CREATE TABLE IF NOT EXISTS especificaciones (
                id TEXT PRIMARY KEY,
                producto TEXT NOT NULL,
                parametro TEXT NOT NULL,
                minimo REAL,
                maximo REAL,
                unidad TEXT NOT NULL DEFAULT '',
                fuente TEXT NOT NULL DEFAULT '',
                estado TEXT NOT NULL DEFAULT '',
                modelado INTEGER NOT NULL DEFAULT 0,
                tipo TEXT NOT NULL DEFAULT '',
                farmacopea TEXT NOT NULL DEFAULT ''
            );
            """
        )
        c.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")


# ---------------------------------------------------------------------------
# Elementos
# ---------------------------------------------------------------------------
def listar_elementos() -> list[Elemento]:
    with get_conn() as c:
        filas = c.execute("SELECT * FROM elementos ORDER BY numero").fetchall()
    return [Elemento(**{**dict(f), "radiactivo": bool(f["radiactivo"])}) for f in filas]


def obtener_elemento(simbolo: str) -> Elemento | None:
    with get_conn() as c:
        fila = c.execute("SELECT * FROM elementos WHERE lower(simbolo) = lower(?)", (simbolo,)).fetchone()
    return Elemento(**{**dict(fila), "radiactivo": bool(fila["radiactivo"])}) if fila else None


# ---------------------------------------------------------------------------
# Compuestos
# ---------------------------------------------------------------------------
def _a_compuesto(f: sqlite3.Row) -> Compuesto:
    d = dict(f)
    d.pop("busqueda", None)
    d["sinonimos"] = json.loads(d["sinonimos"])
    d["pm_aplicable"] = bool(d["pm_aplicable"])
    d["verificado"] = bool(d["verificado"])
    return Compuesto(**d)


def _filtros(q, categoria, fase, acceso, tipo) -> tuple[str, list]:
    where, params = [], []
    if q:
        for palabra in normalizar(q).split():
            where.append("busqueda LIKE ?")
            params.append(f"%{palabra}%")
    for columna, valor in (("categoria", categoria), ("fase", fase), ("acceso", acceso), ("tipo", tipo)):
        if valor:
            where.append(f"{columna} = ?")
            params.append(valor)
    return (" WHERE " + " AND ".join(where)) if where else "", params


def listar_compuestos(
    q: str | None = None,
    categoria: str | None = None,
    fase: str | None = None,
    acceso: str | None = None,
    tipo: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Compuesto]:
    donde, params = _filtros(q, categoria, fase, acceso, tipo)
    sql = f"SELECT * FROM compuestos{donde} ORDER BY rowid"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [limit, offset]
    with get_conn() as c:
        filas = c.execute(sql, params).fetchall()
    return [_a_compuesto(f) for f in filas]


def contar_compuestos(q=None, categoria=None, fase=None, acceso=None, tipo=None) -> int:
    donde, params = _filtros(q, categoria, fase, acceso, tipo)
    with get_conn() as c:
        return c.execute(f"SELECT COUNT(*) FROM compuestos{donde}", params).fetchone()[0]


def obtener_compuesto(id_: str) -> Compuesto | None:
    with get_conn() as c:
        fila = c.execute("SELECT * FROM compuestos WHERE id = ?", (id_,)).fetchone()
    return _a_compuesto(fila) if fila else None


def obtener_compuestos(ids) -> dict[str, Compuesto]:
    """Solo los compuestos pedidos, por id (para simular no hace falta cargar todo el catálogo)."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        return {}
    with get_conn() as c:
        filas = []
        for i in range(0, len(ids), 500):  # SQLite limita la cantidad de parámetros por consulta
            lote = ids[i : i + 500]
            filas += c.execute(f"SELECT * FROM compuestos WHERE id IN ({','.join('?' * len(lote))})", lote).fetchall()
    return {f["id"]: _a_compuesto(f) for f in filas}


def listar_categorias() -> list[dict]:
    """Categorías con su cantidad de compuestos, en el orden de la biblioteca."""
    from app.db.seed import cargar_categorias

    with get_conn() as c:
        cuentas = {f["categoria"]: f["n"] for f in c.execute("SELECT categoria, COUNT(*) n FROM compuestos GROUP BY categoria")}
    return [{"categoria": cat, "total": cuentas.get(cat, 0)} for cat in cargar_categorias()]


# ---------------------------------------------------------------------------
# Reacciones
# ---------------------------------------------------------------------------
def _a_reaccion(c: sqlite3.Connection, f: sqlite3.Row) -> Reaccion:
    partes = c.execute(
        "SELECT * FROM reaccion_participantes WHERE reaccion_id = ? ORDER BY lado DESC, orden", (f["id"],)
    ).fetchall()
    return Reaccion(
        id=f["id"],
        nombre=f["nombre"],
        descripcion=f["descripcion"],
        categoria=f["categoria"],
        reactivos=[Participante(id=p["compuesto_id"], coef=p["coef"]) for p in partes if p["lado"] == "reactivo"],
        productos=[
            ProductoReaccion(id=p["compuesto_id"], coef=p["coef"], principal=bool(p["principal"]))
            for p in partes
            if p["lado"] == "producto"
        ],
        catalizador=f["catalizador"],
        excipiente=f["excipiente"],
        parametros=json.loads(f["parametros"]),
        fuente=f["fuente"],
        estado_validacion=f["estado_validacion"],
    )


def listar_reacciones(compuesto: str | None = None) -> list[Reaccion]:
    """Todas las reacciones, o solo las que usan un compuesto dado (como reactivo, producto o catalizador)."""
    with get_conn() as c:
        if compuesto:
            filas = c.execute(
                "SELECT * FROM reacciones WHERE id IN (SELECT reaccion_id FROM reaccion_participantes WHERE compuesto_id = ?) "
                "OR catalizador = ? OR excipiente = ? ORDER BY rowid",
                (compuesto, compuesto, compuesto),
            ).fetchall()
        else:
            filas = c.execute("SELECT * FROM reacciones ORDER BY rowid").fetchall()
        return [_a_reaccion(c, f) for f in filas]


def obtener_reaccion(id_: str) -> Reaccion | None:
    with get_conn() as c:
        fila = c.execute("SELECT * FROM reacciones WHERE id = ?", (id_,)).fetchone()
        return _a_reaccion(c, fila) if fila else None


# ---------------------------------------------------------------------------
# Especificaciones
# ---------------------------------------------------------------------------
def listar_especificaciones() -> list[Especificacion]:
    with get_conn() as c:
        filas = c.execute("SELECT * FROM especificaciones ORDER BY rowid").fetchall()
    return [Especificacion(**{**dict(f), "modelado": bool(f["modelado"])}) for f in filas]
