from fastapi import APIRouter, HTTPException

from app.db import database
from app.models.schemas import Elemento

router = APIRouter(tags=["elementos"])


@router.get("/elementos", response_model=list[Elemento])
def listar_elementos():
    """Los 118 elementos con su masa atómica (NIST). Sirven para calcular el peso molecular de cualquier fórmula."""
    return database.listar_elementos()


@router.get("/elementos/{simbolo}", response_model=Elemento)
def obtener_elemento(simbolo: str):
    e = database.obtener_elemento(simbolo)
    if e is None:
        raise HTTPException(status_code=404, detail="Elemento no encontrado")
    return e
