from fastapi import APIRouter, HTTPException

from app.core import reacciones as util_reacciones
from app.core.pedido import ReaccionDesconocida, ejecutar
from app.core.simulador import REACCION_POR_DEFECTO, ComponenteDesconocido
from app.db import database
from app.models.schemas import ReaccionDetalle, SimulacionEntrada, SimulacionSalida

router = APIRouter(tags=["simulacion"])


def _catalogo() -> dict:
    return {c.id: c for c in database.listar_compuestos()}


def _reaccion_o_404(id_: str):
    r = database.obtener_reaccion(id_)
    if r is None:
        raise HTTPException(status_code=404, detail=f"Reacción desconocida: {id_}")
    return r


@router.get("/reacciones", response_model=list[ReaccionDetalle])
def listar_reacciones(compuesto: str | None = None):
    """Reacciones disponibles. Con `compuesto` se listan solo las que lo usan (reactivo, producto o catalizador)."""
    reacciones = database.listar_reacciones(compuesto)
    ids = {p.id for r in reacciones for p in [*r.reactivos, *r.productos]}
    ids |= {x for r in reacciones for x in (r.catalizador, r.excipiente) if x}
    catalogo = database.obtener_compuestos(ids)
    return [util_reacciones.detallar(r, catalogo) for r in reacciones]


@router.get("/reacciones/{reaccion_id}", response_model=ReaccionDetalle)
def obtener_reaccion(reaccion_id: str):
    r = _reaccion_o_404(reaccion_id)
    ids = {p.id for p in [*r.reactivos, *r.productos]} | {x for x in (r.catalizador, r.excipiente) if x}
    return util_reacciones.detallar(r, database.obtener_compuestos(ids))


@router.get("/reaccion", response_model=ReaccionDetalle)
def reaccion_activa(id: str = REACCION_POR_DEFECTO):
    """Reacción y parámetros del modelo en uso (para mostrarlos y auditarlos). Por defecto, la del ibuprofeno."""
    return obtener_reaccion(id)


@router.post("/simulacion", response_model=SimulacionSalida)
def simulacion(entrada: SimulacionEntrada):
    """Simula una mezcla.

    Cantidades en g, kg, mg, mL, L, mol o mmol; soluciones con `concentracion` aparte de la `pureza`.
    Con `incertidumbre` la respuesta trae intervalos (p5–p95). Con `mediciones` se evalúa la
    especificación de varios parámetros: lo que no se midió figura como «sin dato», no como cumplido.
    """
    try:
        salida, _ = ejecutar(entrada)
    except ReaccionDesconocida as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ComponenteDesconocido as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return salida
