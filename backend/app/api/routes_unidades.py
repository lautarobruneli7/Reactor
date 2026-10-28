"""Conversión de unidades y concentraciones: calculadoras de laboratorio."""
from fastapi import APIRouter, HTTPException

from app.core import formulas, unidades
from app.db import database
from app.models.schemas import EntradaConcentracion, EntradaConversion

router = APIRouter(tags=["unidades"])


def _compuesto_o_404(id_: str):
    c = database.obtener_compuesto(id_)
    if c is None:
        raise HTTPException(status_code=404, detail="Compuesto no encontrado")
    return c


@router.get("/compuestos/{compuesto_id}/densidad")
def densidad(compuesto_id: str):
    """Densidad del líquido puro (g/mL) con su temperatura y fuente. 404 si el catálogo no la tiene."""
    _compuesto_o_404(compuesto_id)
    d = unidades.densidad_pura(compuesto_id)
    if d is None:
        raise HTTPException(status_code=404, detail="No hay densidad cargada para este compuesto: informala vos en la simulación")
    return d


@router.post("/unidades/convertir")
def convertir(entrada: EntradaConversion):
    """Convierte una cantidad de un compuesto entre g, kg, mg, mL, L, mol y mmol.

    Los moles son netos del compuesto (descuentan pureza y concentración). Para pasar volumen
    a masa hace falta la densidad; para soluciones hay que informarla.
    """
    c = _compuesto_o_404(entrada.compuesto_id)
    try:
        return unidades.convertir(
            c, entrada.cantidad, entrada.unidad, entrada.a_unidad,
            pureza=entrada.pureza, concentracion=entrada.concentracion, densidad_g_ml=entrada.densidad_g_ml,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/soluciones/convertir")
def convertir_concentracion(entrada: EntradaConcentracion):
    """Expresa una concentración como %p/p, %p/v y molar (las dos últimas necesitan la densidad de la solución)."""
    try:
        if entrada.compuesto_id is not None:
            c = _compuesto_o_404(entrada.compuesto_id)
            pm = c.pm if c.pm_aplicable else 0.0
        else:
            pm = formulas.peso_molecular(entrada.formula)  # type: ignore[arg-type]
        return {"pm": pm, **unidades.convertir_concentracion(entrada.concentracion, pm, entrada.densidad_g_ml)}
    except (ValueError, formulas.FormulaInvalida) as e:
        raise HTTPException(status_code=422, detail=str(e))
