import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import (
    routes_auth,
    routes_calculos,
    routes_compuestos,
    routes_elementos,
    routes_ensayos,
    routes_simulacion,
    routes_unidades,
)
from app.core import servicio_ensayos
from app.core.propiedades import rdkit_disponible
from app.db import datos
from app.db.database import init_db
from app.db.seed import cargar_datos

log = logging.getLogger("retorta")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    cargar_datos()  # el catálogo se rehace desde los JSON (no guarda nada del usuario)
    config.secreto()  # con SIM_AUTH=on falla acá, al arrancar, si falta la clave de firma
    datos.init_datos()  # usuarios, ensayos y auditoría: persistentes
    if config.auth_activa():
        if servicio_ensayos.asegurar_admin_inicial() is None and not any(u.email != servicio_ensayos.EMAIL_LOCAL for u in servicio_ensayos.listar_usuarios()):
            log.warning("No hay usuarios: creá el primero con SIM_ADMIN_EMAIL y SIM_ADMIN_CLAVE o con scripts/crear_usuario.py")
    else:
        servicio_ensayos.asegurar_usuario_local()
    yield


app = FastAPI(
    title="Simulador Químico",
    description="Estimación de rendimiento, pureza y calidad de mezclas para las reacciones del catálogo (ejemplo principal: ibuprofeno). "
    "No reemplaza ensayos de laboratorio.",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.origenes_cors(),
    allow_methods=["*"],
    expose_headers=["X-Total-Count", "Content-Disposition"],
    allow_headers=["*"],
)

app.include_router(routes_compuestos.router, prefix="/api")
app.include_router(routes_elementos.router, prefix="/api")
app.include_router(routes_calculos.router, prefix="/api")
app.include_router(routes_unidades.router, prefix="/api")
app.include_router(routes_simulacion.router, prefix="/api")
app.include_router(routes_auth.router, prefix="/api")
app.include_router(routes_ensayos.router, prefix="/api")


@app.get("/api/salud", tags=["sistema"])
def salud():
    return {"estado": "ok", "rdkit": rdkit_disponible(), "version": config.VERSION}


# Frontend ya compilado (Docker / producción): se sirve desde el mismo origen, sin CORS. Va al final para no tapar /api.
_estatica = config.carpeta_estatica()
if _estatica is not None:
    app.mount("/", StaticFiles(directory=_estatica, html=True), name="frontend")
