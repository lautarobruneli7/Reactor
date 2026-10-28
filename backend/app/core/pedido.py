"""Ejecuta un pedido de simulación contra el catálogo: lo comparten la simulación en vivo y el guardado de ensayos."""
from __future__ import annotations

from app.core import incertidumbre
from app.core.simulador import simular
from app.db import database
from app.models.schemas import Reaccion, SimulacionEntrada, SimulacionSalida


class ReaccionDesconocida(LookupError):
    pass


def ejecutar(entrada: SimulacionEntrada) -> tuple[SimulacionSalida, Reaccion]:
    """Simula y, si se pidió, calcula la incertidumbre. Levanta ComponenteDesconocido / ValueError / ReaccionDesconocida.

    Solo se leen del catálogo los compuestos que importan (los de la reacción y los de la mezcla), no todos:
    con catálogos de miles de sustancias leerlos todos en cada pedido sería lo que más tarda.
    """
    reaccion = database.obtener_reaccion(entrada.reaccion_id)
    if reaccion is None:
        raise ReaccionDesconocida(f"Reacción desconocida: {entrada.reaccion_id}")
    necesarios = {p.id for p in [*reaccion.reactivos, *reaccion.productos]}
    necesarios |= {x for x in (reaccion.catalizador, reaccion.excipiente) if x}
    necesarios |= {c.id for c in entrada.componentes}
    catalogo = database.obtener_compuestos(necesarios)
    specs = database.listar_especificaciones()
    rend, _ = incertidumbre.rendimiento_medido(entrada)
    salida = simular(
        entrada.componentes, catalogo, reaccion, rend,
        pureza_real_pct=entrada.pureza_real_pct, especificaciones=specs, mediciones=entrada.mediciones,
    )
    if entrada.incertidumbre is not None and salida.resultado is not None:
        salida.resultado.incertidumbre = incertidumbre.analizar(entrada, catalogo, reaccion, entrada.incertidumbre, specs)
    return salida, reaccion
