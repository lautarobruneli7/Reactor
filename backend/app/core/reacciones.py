"""Validación y descripción de reacciones contra el catálogo."""
from app.core.balanceo import ecuacion_texto, esta_balanceada
from app.models.schemas import Compuesto, Reaccion, ReaccionDetalle


class ReaccionInvalida(ValueError):
    pass


def _formula(catalogo: dict[str, Compuesto], id_: str, reaccion_id: str) -> str:
    c = catalogo.get(id_)
    if c is None:
        raise ReaccionInvalida(f"{reaccion_id}: el compuesto {id_!r} no está en el catálogo")
    if not c.formula:
        raise ReaccionInvalida(f"{reaccion_id}: {c.nombre} no tiene fórmula")
    return c.formula


def validar(reaccion: Reaccion, catalogo: dict[str, Compuesto]) -> None:
    """Falla si la reacción referencia algo que no existe o si no conserva los átomos."""
    for p in [*reaccion.reactivos, *reaccion.productos]:
        c = catalogo.get(p.id)
        if c is None:
            raise ReaccionInvalida(f"{reaccion.id}: el compuesto {p.id!r} no está en el catálogo")
        if not c.pm_aplicable or c.pm <= 0:
            raise ReaccionInvalida(f"{reaccion.id}: {c.nombre} no tiene peso molecular y no puede ser reactivo ni producto")
    for extra in (reaccion.catalizador, reaccion.excipiente):
        if extra and extra not in catalogo:
            raise ReaccionInvalida(f"{reaccion.id}: el compuesto {extra!r} no está en el catálogo")
    r = [(_formula(catalogo, p.id, reaccion.id), p.coef) for p in reaccion.reactivos]
    pr = [(_formula(catalogo, p.id, reaccion.id), p.coef) for p in reaccion.productos]
    if not esta_balanceada(r, pr):
        raise ReaccionInvalida(f"{reaccion.id}: la ecuación {ecuacion_texto(r, pr)} no conserva los átomos")


def detallar(reaccion: Reaccion, catalogo: dict[str, Compuesto]) -> ReaccionDetalle:
    r = [(catalogo[p.id].formula or "", p.coef) for p in reaccion.reactivos]
    pr = [(catalogo[p.id].formula or "", p.coef) for p in reaccion.productos]
    principal = catalogo[reaccion.principal.id]
    return ReaccionDetalle(
        **reaccion.model_dump(),
        ecuacion=ecuacion_texto(r, pr),
        balanceada=esta_balanceada(r, pr),
        producto={
            "id": principal.id,
            "nombre": principal.nombre,
            "pm": principal.pm,
            "formula": principal.formula,
            "smiles": principal.smiles,
        },
    )
