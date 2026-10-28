from fastapi import APIRouter, HTTPException, Query, Response

from app.core.propiedades import propiedades_moleculares
from app.db import database
from app.models.schemas import Compuesto, Especificacion

router = APIRouter(tags=["compuestos"])


@router.get("/compuestos", response_model=list[Compuesto])
def listar_compuestos(
    response: Response,
    q: str | None = Query(None, description="Texto a buscar en nombre, fórmula, CAS o sinónimos (sin importar acentos)"),
    categoria: str | None = None,
    fase: str | None = Query(None, description="líquido, sólido o gas"),
    acceso: str | None = Query(None, description="libre o controlado"),
    tipo: str | None = None,
    limit: int | None = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Catálogo de compuestos, con búsqueda y filtros. El total sin paginar va en el encabezado X-Total-Count."""
    response.headers["X-Total-Count"] = str(database.contar_compuestos(q, categoria, fase, acceso, tipo))
    return database.listar_compuestos(q, categoria, fase, acceso, tipo, limit, offset)


@router.get("/categorias")
def listar_categorias():
    """Categorías de la biblioteca con la cantidad de compuestos de cada una."""
    return database.listar_categorias()


@router.get("/compuestos/{compuesto_id}", response_model=Compuesto)
def obtener_compuesto(compuesto_id: str):
    c = database.obtener_compuesto(compuesto_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Compuesto no encontrado")
    return c


@router.get("/compuestos/{compuesto_id}/propiedades")
def propiedades(compuesto_id: str):
    """Propiedades estimadas con RDKit (si está instalado)."""
    c = database.obtener_compuesto(compuesto_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Compuesto no encontrado")
    props = propiedades_moleculares(c.smiles)
    if props is None:
        raise HTTPException(
            status_code=501,
            detail="Propiedades no disponibles: falta RDKit (pip install '.[quimica]') o el compuesto no tiene estructura.",
        )
    return props


@router.get("/especificaciones", response_model=list[Especificacion])
def listar_especificaciones():
    return database.listar_especificaciones()
