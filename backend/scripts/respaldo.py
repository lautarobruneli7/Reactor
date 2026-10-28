"""Respaldo y verificación de la base persistente (usuarios, ensayos, auditoría).

    python scripts/respaldo.py respaldar [carpeta]   copia consistente + hash de la cadena de auditoría
    python scripts/respaldo.py verificar              verifica la cadena de hashes e imprime el último hash

SQLite: copia con la API de respaldo de SQLite (consistente aunque el servidor esté escribiendo).
PostgreSQL: usa pg_dump (tiene que estar instalado).
Guardá el último hash por fuera del sistema (otro equipo, papel firmado): permite detectar que alguien reescribió toda la cadena.
"""
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

from app import config
from app.db import datos


def verificar() -> dict:
    with datos.motor().connect() as c:
        return datos.verificar_cadena(c)


def respaldar(carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    url = make_url(config.url_datos())
    if url.get_backend_name() == "sqlite":
        destino = carpeta / f"retorta-{marca}.db"
        origen = sqlite3.connect(url.database)
        copia = sqlite3.connect(destino)
        with copia:
            origen.backup(copia)
        origen.close()
        copia.close()
    else:
        if not shutil.which("pg_dump"):
            raise SystemExit("No se encontró pg_dump: instalá el cliente de PostgreSQL")
        destino = carpeta / f"retorta-{marca}.sql"
        subprocess.run(
            ["pg_dump", "--no-owner", "-f", str(destino), f"postgresql://{url.username}@{url.host}:{url.port or 5432}/{url.database}"],
            check=True, env={**__import__("os").environ, "PGPASSWORD": url.password or ""},
        )
    return destino


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "verificar":
        v = verificar()
        print(json.dumps({k: v[k] for k in ("ok", "registros", "ultimo_hash", "total_errores")}, indent=2))
        return 0 if v["ok"] else 1
    if cmd == "respaldar":
        v = verificar()
        destino = respaldar(Path(sys.argv[2] if len(sys.argv) > 2 else "respaldos"))
        (destino.with_suffix(".verificacion.json")).write_text(json.dumps({k: v[k] for k in ("ok", "registros", "ultimo_hash", "total_errores")}, indent=2))
        print(f"Respaldo: {destino}\nCadena de auditoría: {'OK' if v['ok'] else 'CON ERRORES'} ({v['registros']} registros)\nÚltimo hash: {v['ultimo_hash']}")
        return 0 if v["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
