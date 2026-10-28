"""Cálculos que no dependen del catálogo: sirven para cualquier fórmula."""
from fastapi import APIRouter, HTTPException, Query

from app.core import formulas
from app.core.balanceo import NoBalanceable, balancear, ecuacion_texto
from app.models.schemas import EntradaBalanceo

router = APIRouter(tags=["calculos"])


@router.get("/formulas/pm")
def peso_molecular(formula: str = Query(..., min_length=1, max_length=200, examples=["C13H18O2", "CuSO4·5H2O"])):
    """Peso molecular, fórmula de Hill y composición porcentual de cualquier fórmula."""
    try:
        comp = formulas.composicion(formula)
        return {
            "formula": formula,
            "formula_hill": formulas.formula_hill(comp),
            "pm": round(formulas.peso_molecular(formula), 4),
            "composicion": formulas.composicion_porcentual(formula),
        }
    except formulas.FormulaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/estequiometria/balancear")
def balancear_ecuacion(entrada: EntradaBalanceo):
    """Balancea una ecuación a partir de las fórmulas de reactivos y productos.

    Devuelve los coeficientes enteros más chicos y los gramos de cada especie por cada mol de reacción.
    """
    try:
        cr, cp = balancear(entrada.reactivos, entrada.productos)
        reactivos = [{"formula": f, "coef": c, "pm": round(formulas.peso_molecular(f), 4)} for f, c in zip(entrada.reactivos, cr)]
        productos = [{"formula": f, "coef": c, "pm": round(formulas.peso_molecular(f), 4)} for f, c in zip(entrada.productos, cp)]
    except (formulas.FormulaInvalida, NoBalanceable) as e:
        raise HTTPException(status_code=422, detail=str(e))
    for x in (*reactivos, *productos):
        x["gramos_por_mol_de_reaccion"] = round(x["coef"] * x["pm"], 4)
    return {
        "ecuacion": ecuacion_texto([(x["formula"], x["coef"]) for x in reactivos], [(x["formula"], x["coef"]) for x in productos]),
        "reactivos": reactivos,
        "productos": productos,
    }
