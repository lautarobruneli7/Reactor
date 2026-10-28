"""Configuración por variables de entorno. Se lee en el momento de usarla (así los tests pueden cambiarla).

SIM_DATABASE_URL   Base persistente de la aplicación (usuarios, ensayos, auditoría).
                   sqlite:///ruta.db (por defecto: backend/retorta_datos.db) o
                   postgresql+psycopg://usuario:clave@host:5432/base
SIM_DB_PATH        Base DERIVADA del catálogo (se rehace sola en cada arranque; no guarda nada del usuario).
SIM_AUTH           "on" para exigir login; cualquier otra cosa = modo local de un solo usuario (sin login).
SIM_SECRET         Clave para firmar los tokens (32 caracteres o más). Obligatoria con SIM_AUTH=on.
SIM_TOKEN_HORAS    Vigencia del token en horas (8 por defecto).
SIM_ADMIN_EMAIL / SIM_ADMIN_CLAVE
                   Crean el primer administrador si todavía no hay usuarios.
SIM_CORS_ORIGINS   Orígenes permitidos separados por coma (por defecto, el servidor de desarrollo del frontend).
SIM_STATIC_DIR     Carpeta con el frontend ya compilado; si existe, el backend la sirve en "/".
"""
import os
from pathlib import Path

VERSION = "0.4.0"
RAIZ_BACKEND = Path(__file__).resolve().parents[1]


def url_datos() -> str:
    return os.getenv("SIM_DATABASE_URL") or f"sqlite:///{RAIZ_BACKEND / 'retorta_datos.db'}"


def auth_activa() -> bool:
    return os.getenv("SIM_AUTH", "").strip().lower() in {"on", "1", "true", "si", "sí", "yes"}


def secreto() -> str:
    s = os.getenv("SIM_SECRET", "")
    if auth_activa() and len(s) < 32:
        raise RuntimeError(
            "Con SIM_AUTH=on hace falta SIM_SECRET de 32 caracteres o más (por ejemplo: python -c \"import secrets; print(secrets.token_urlsafe(48))\")"
        )
    return s or "modo-local-sin-login-no-usar-en-produccion"


def token_horas() -> float:
    try:
        return float(os.getenv("SIM_TOKEN_HORAS", "8"))
    except ValueError:
        return 8.0


def origenes_cors() -> list[str]:
    crudo = os.getenv("SIM_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip() for o in crudo.split(",") if o.strip()]


def carpeta_estatica() -> Path | None:
    d = os.getenv("SIM_STATIC_DIR")
    return Path(d) if d and Path(d).is_dir() else None
