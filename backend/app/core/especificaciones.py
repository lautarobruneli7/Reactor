"""Evaluación de un producto contra una especificación de VARIOS parámetros.

El modelo estima hoy un solo parámetro (la pureza). Los demás (pérdida por secado, sustancias
relacionadas, residuo de ignición, metales pesados, solventes residuales...) se cargan como
mediciones del ensayo. Reglas:

- Un parámetro sin límite cargado se informa como `sin_limite`: NO se da por cumplido.
- Un parámetro con límite pero sin medición se informa como `sin_dato`: tampoco.
- El cumplimiento global es «cumple» solo si hay al menos un parámetro y TODOS cumplen.
"""
from app.models.schemas import EvaluacionEspecificacion, Especificacion


def _limite_texto(s: Especificacion) -> str:
    return s.estado or ("sin límite cargado" if s.minimo is None and s.maximo is None else "")


def evaluar(
    specs: list[Especificacion],
    producto_id: str,
    pureza_valor: float,
    pureza_origen: str,
    mediciones: dict[str, float],
) -> tuple[list[EvaluacionEspecificacion], str, list[str]]:
    """Devuelve (evaluación por parámetro, cumplimiento global, avisos)."""
    avisos: list[str] = []
    todas = {s.id: s for s in specs}
    desconocidas = [k for k in mediciones if k not in todas]
    if desconocidas:
        validos = ", ".join(sorted(todas)) or "(no hay especificaciones cargadas)"
        raise ValueError(
            f"Medición para una especificación que no existe: {', '.join(sorted(desconocidas))}. Ids válidos: {validos}"
        )
    de_otro = [k for k in mediciones if todas[k].producto != producto_id]
    if de_otro:
        avisos.append("Se ignoraron mediciones de otro producto: " + ", ".join(sorted(de_otro)))

    out: list[EvaluacionEspecificacion] = []
    for s in specs:
        if s.producto != producto_id:
            continue
        if s.modelado:
            valor: float | None = pureza_valor
            origen = "medido" if pureza_origen == "experimental" else "modelo"
        elif s.id in mediciones:
            valor, origen = mediciones[s.id], "medido"
        else:
            valor, origen = None, None
        if s.minimo is None and s.maximo is None:
            estado = "sin_limite"
        elif valor is None:
            estado = "sin_dato"
        else:
            ok = (s.minimo is None or valor >= s.minimo) and (s.maximo is None or valor <= s.maximo)
            estado = "cumple" if ok else "no_cumple"
        out.append(
            EvaluacionEspecificacion(
                id=s.id, parametro=s.parametro, unidad=s.unidad, minimo=s.minimo, maximo=s.maximo,
                valor=valor, origen=origen, estado=estado, modelado=s.modelado, fuente=s.fuente,
                estado_limite=_limite_texto(s),
            )
        )

    if not out:
        return out, "sin_especificaciones", avisos
    if any(x.estado == "no_cumple" for x in out):
        return out, "no_cumple", avisos
    if all(x.estado == "cumple" for x in out):
        return out, "cumple", avisos
    return out, "incompleto", avisos
