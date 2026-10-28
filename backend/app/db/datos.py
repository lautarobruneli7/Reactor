"""Base persistente de la aplicación: usuarios, ensayos, eventos y registro de auditoría.

A diferencia del catálogo (`database.py`, una copia derivada de los JSON que se rehace en cada arranque),
ESTA base guarda lo que crean las personas y no se rehace nunca: hay que respaldarla (ver `scripts/respaldo.py`).

Funciona con SQLite (por defecto) y con PostgreSQL (`SIM_DATABASE_URL=postgresql+psycopg://...`).

Inalterabilidad: `ensayos`, `eventos` y `registro` no admiten UPDATE, DELETE ni TRUNCATE (lo impide la propia
base con disparadores). Corregir un ensayo es crear otro que lo reemplaza. Además `registro` es una cadena de
hashes: cada fila incluye el hash de la anterior, así que cualquier modificación o borrado hecho por fuera de la
aplicación se detecta con `verificar_cadena` (es evidencia de alteración, no una barrera contra quien administra la base:
conviene guardar el último hash por fuera, ver `GET /api/auditoria/verificar`).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    event,
    insert,
    select,
    text,
)
from sqlalchemy.engine import Connection, Engine

from app import config

GENESIS = "0" * 64
VERSION_ESQUEMA = 1

metadata = MetaData()

meta = Table(
    "meta", metadata,
    Column("clave", String(50), primary_key=True),
    Column("valor", String(200), nullable=False),
)

usuarios = Table(
    "usuarios", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(200), nullable=False, unique=True),
    Column("nombre", String(200), nullable=False),
    Column("rol", String(20), nullable=False),
    Column("clave_hash", Text, nullable=False),
    Column("activo", Boolean, nullable=False),
    Column("creado_en", String(40), nullable=False),
)

ensayos = Table(
    "ensayos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("creado_en", String(40), nullable=False),
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=False),
    Column("reaccion_id", String(100), nullable=False),
    Column("lote", String(100)),
    Column("notas", Text, nullable=False),
    Column("entrada", Text, nullable=False),
    Column("resultado", Text, nullable=False),
    Column("version_modelo", String(100), nullable=False),
    Column("corrige_a", Integer, ForeignKey("ensayos.id")),
    Column("digest", String(64), nullable=False),
)

eventos = Table(
    "eventos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ensayo_id", Integer, ForeignKey("ensayos.id"), nullable=False),
    Column("tipo", String(20), nullable=False),
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=False),
    Column("creado_en", String(40), nullable=False),
    Column("comentario", Text, nullable=False),
    Column("digest", String(64), nullable=False),
)

registro = Table(
    "registro", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("creado_en", String(40), nullable=False),
    Column("usuario_id", Integer, ForeignKey("usuarios.id")),
    Column("accion", String(40), nullable=False),
    Column("entidad", String(20), nullable=False),
    Column("entidad_id", Integer),
    Column("detalle", Text, nullable=False),
    Column("prev_hash", String(64), nullable=False, unique=True),
    Column("hash", String(64), nullable=False, unique=True),
)

TABLAS_INALTERABLES = ("ensayos", "eventos", "registro")


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------
_motor: Engine | None = None
_url_del_motor: str | None = None


def motor() -> Engine:
    """Motor de SQLAlchemy; se vuelve a crear si cambió SIM_DATABASE_URL (los tests lo cambian)."""
    global _motor, _url_del_motor
    url = config.url_datos()
    if _motor is None or _url_del_motor != url:
        if _motor is not None:
            _motor.dispose()
        args: dict[str, Any] = {}
        if url.startswith("sqlite"):
            args["connect_args"] = {"check_same_thread": False, "timeout": 30}
        _motor = create_engine(url, pool_pre_ping=True, **args)
        if url.startswith("sqlite"):

            @event.listens_for(_motor, "connect")
            def _pragmas(dbapi_con, _):  # pragma: no cover - lo ejecuta SQLAlchemy
                cur = dbapi_con.cursor()
                cur.execute("PRAGMA foreign_keys = ON")
                cur.close()

        _url_del_motor = url
    return _motor


def dialecto() -> str:
    return motor().dialect.name


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonico(obj: Any) -> str:
    """JSON determinista (claves ordenadas, sin espacios): lo que se hashea."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Creación del esquema y disparadores de inalterabilidad
# ---------------------------------------------------------------------------
def _disparadores_sqlite(conn: Connection) -> None:
    for t in TABLAS_INALTERABLES:
        for op in ("UPDATE", "DELETE"):
            conn.execute(text(
                f"CREATE TRIGGER IF NOT EXISTS {t}_inalterable_{op.lower()} BEFORE {op} ON {t} "
                f"BEGIN SELECT RAISE(ABORT, 'La tabla {t} es inalterable: no admite {op}'); END"
            ))


def _disparadores_postgres(conn: Connection) -> None:
    conn.execute(text(
        "CREATE OR REPLACE FUNCTION retorta_inalterable() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'La tabla % es inalterable: no admite %', TG_TABLE_NAME, TG_OP; END; "
        "$$ LANGUAGE plpgsql"
    ))
    for t in TABLAS_INALTERABLES:
        conn.execute(text(f"DROP TRIGGER IF EXISTS {t}_inalterable ON {t}"))
        conn.execute(text(
            f"CREATE TRIGGER {t}_inalterable BEFORE UPDATE OR DELETE ON {t} "
            f"FOR EACH ROW EXECUTE FUNCTION retorta_inalterable()"
        ))
        conn.execute(text(f"DROP TRIGGER IF EXISTS {t}_sin_truncate ON {t}"))
        conn.execute(text(
            f"CREATE TRIGGER {t}_sin_truncate BEFORE TRUNCATE ON {t} "
            f"FOR EACH STATEMENT EXECUTE FUNCTION retorta_inalterable()"
        ))


def init_datos() -> None:
    """Crea las tablas y los disparadores si no existen (se puede llamar en cada arranque)."""
    eng = motor()
    metadata.create_all(eng)
    with eng.begin() as conn:
        if eng.dialect.name == "sqlite":
            _disparadores_sqlite(conn)
        elif eng.dialect.name == "postgresql":
            _disparadores_postgres(conn)
        else:  # pragma: no cover
            raise RuntimeError(f"Base no soportada: {eng.dialect.name} (usar SQLite o PostgreSQL)")
        actual = conn.execute(select(meta.c.valor).where(meta.c.clave == "version_esquema")).scalar()
        if actual is None:
            conn.execute(insert(meta).values(clave="version_esquema", valor=str(VERSION_ESQUEMA)))
        elif int(actual) > VERSION_ESQUEMA:
            raise RuntimeError(
                f"La base de datos tiene el esquema {actual}, más nuevo que el de este programa ({VERSION_ESQUEMA}): actualizá el programa"
            )


# ---------------------------------------------------------------------------
# Cadena de hashes
# ---------------------------------------------------------------------------
def _cuerpo_registro(creado_en: str, usuario_id: int | None, accion: str, entidad: str, entidad_id: int | None, detalle: str) -> str:
    return canonico(
        {"creado_en": creado_en, "usuario_id": usuario_id, "accion": accion, "entidad": entidad, "entidad_id": entidad_id, "detalle": detalle}
    )


def hash_registro(prev_hash: str, creado_en: str, usuario_id: int | None, accion: str, entidad: str, entidad_id: int | None, detalle: str) -> str:
    return sha256(prev_hash + "|" + _cuerpo_registro(creado_en, usuario_id, accion, entidad, entidad_id, detalle))


def anexar_registro(
    conn: Connection, *, usuario_id: int | None, accion: str, entidad: str, entidad_id: int | None, detalle: dict[str, Any]
) -> dict[str, Any]:
    """Agrega una fila a la cadena. Dos escrituras simultáneas con el mismo `prev_hash` chocan contra la
    restricción UNIQUE: la segunda falla y quien llama reintenta la operación completa (ver `con_reintentos`)."""
    ultimo = conn.execute(select(registro.c.hash).order_by(registro.c.id.desc()).limit(1)).scalar()
    prev = ultimo or GENESIS
    creado = ahora()
    det = canonico(detalle)
    h = hash_registro(prev, creado, usuario_id, accion, entidad, entidad_id, det)
    res = conn.execute(insert(registro).values(
        creado_en=creado, usuario_id=usuario_id, accion=accion, entidad=entidad, entidad_id=entidad_id,
        detalle=det, prev_hash=prev, hash=h,
    ))
    return {"id": res.inserted_primary_key[0], "hash": h, "prev_hash": prev, "creado_en": creado}


def con_reintentos(operacion, intentos: int = 6):
    """Ejecuta `operacion()` (que abre su propia transacción) y la repite si otra escritura se coló en la cadena."""
    from sqlalchemy.exc import IntegrityError

    ultimo: Exception | None = None
    for _ in range(intentos):
        try:
            return operacion()
        except IntegrityError as e:  # colisión de prev_hash: otra escritura ganó
            if "prev_hash" not in str(e).lower() and "registro" not in str(e).lower():
                raise
            ultimo = e
    raise RuntimeError("No se pudo registrar la operación por escrituras simultáneas; reintentá") from ultimo


def verificar_cadena(conn: Connection) -> dict[str, Any]:
    """Recorre el registro desde el principio y comprueba (1) los enlaces entre hashes, (2) cada hash y (3) que cada
    ensayo o evento citado siga igual que cuando se registró."""
    errores: list[dict[str, Any]] = []
    prev = GENESIS
    n = 0
    ultimo_hash = GENESIS
    ens_ok = ev_ok = 0
    filas = conn.execute(select(registro).order_by(registro.c.id)).mappings()
    for f in filas:
        n += 1
        if f["prev_hash"] != prev:
            errores.append({"registro_id": f["id"], "motivo": "el enlace con el registro anterior no coincide (hay filas borradas, agregadas o cambiadas)"})
        esperado = hash_registro(f["prev_hash"], f["creado_en"], f["usuario_id"], f["accion"], f["entidad"], f["entidad_id"], f["detalle"])
        if esperado != f["hash"]:
            errores.append({"registro_id": f["id"], "motivo": "el contenido de la fila no coincide con su hash (fue modificada)"})
        det = json.loads(f["detalle"])
        if f["entidad"] == "ensayo" and f["accion"] == "ensayo.crear":
            fila = conn.execute(select(ensayos).where(ensayos.c.id == f["entidad_id"])).mappings().first()
            if fila is None:
                errores.append({"registro_id": f["id"], "motivo": f"el ensayo {f['entidad_id']} fue borrado"})
            elif digest_ensayo(fila) != det.get("digest") or fila["digest"] != det.get("digest"):
                errores.append({"registro_id": f["id"], "motivo": f"el ensayo {f['entidad_id']} fue modificado después de registrarse"})
            else:
                ens_ok += 1
        elif f["entidad"] == "evento":
            fila = conn.execute(select(eventos).where(eventos.c.id == f["entidad_id"])).mappings().first()
            if fila is None:
                errores.append({"registro_id": f["id"], "motivo": f"el evento {f['entidad_id']} fue borrado"})
            elif digest_evento(fila) != det.get("digest") or fila["digest"] != det.get("digest"):
                errores.append({"registro_id": f["id"], "motivo": f"el evento {f['entidad_id']} fue modificado después de registrarse"})
            else:
                ev_ok += 1
        prev = f["hash"]
        ultimo_hash = f["hash"]
    # filas de ensayos/eventos que nunca entraron al registro
    citados_e = {f for f in conn.execute(select(registro.c.entidad_id).where(registro.c.accion == "ensayo.crear")).scalars()}
    for (eid,) in conn.execute(select(ensayos.c.id)):
        if eid not in citados_e:
            errores.append({"registro_id": None, "motivo": f"el ensayo {eid} no figura en el registro"})
    return {
        "ok": not errores,
        "registros": n,
        "ensayos_verificados": ens_ok,
        "eventos_verificados": ev_ok,
        "ultimo_hash": ultimo_hash,
        "errores": errores[:50],
        "total_errores": len(errores),
    }


def digest_ensayo(fila: Any) -> str:
    return sha256(canonico({
        "creado_en": fila["creado_en"], "usuario_id": fila["usuario_id"], "reaccion_id": fila["reaccion_id"],
        "lote": fila["lote"], "notas": fila["notas"], "entrada": fila["entrada"], "resultado": fila["resultado"],
        "version_modelo": fila["version_modelo"], "corrige_a": fila["corrige_a"],
    }))


def digest_evento(fila: Any) -> str:
    return sha256(canonico({
        "ensayo_id": fila["ensayo_id"], "tipo": fila["tipo"], "usuario_id": fila["usuario_id"],
        "creado_en": fila["creado_en"], "comentario": fila["comentario"],
    }))
