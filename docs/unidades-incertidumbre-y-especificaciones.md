# Unidades, soluciones, incertidumbre y especificaciones

Complementa `supuestos-del-modelo.md` con lo que se agregó después. Lo que sigue describe qué hace el programa y **qué no garantiza**.

## Cantidades y unidades

Cada insumo se carga en **g, kg, mg, mL, L, mol o mmol** (`gramos`, o `cantidad` + `unidad`, nunca las dos).

- **mL / L** necesitan la densidad del material tal como se carga. Para un líquido puro se toma de `app/data/densidades.json`; si el usuario informa `densidad_g_ml`, esa manda. **Si no hay densidad confiable, el programa se niega a convertir y lo dice**: no inventa un valor.
- **mol / mmol** son moles **netos** del compuesto: ya descuentan pureza y concentración. Gramos de material = mol · PM / (pureza · fracción de soluto).
- Un compuesto sin peso molecular único (polímeros) no se puede cargar en moles.

## Pureza y concentración son dos datos distintos

- **Pureza**: qué parte del compuesto es el compuesto buscado. Lo que falta es **impureza** y el modelo la castiga.
- **Concentración** (solución): `p/p` (% en masa), `p/v` (g cada 100 mL de solución) o `molar`. Lo que falta es **solvente**, que no se cuenta como impureza.

HCl 37 % p/p ⇒ 100 g de solución = 37 g de HCl. Cargarlo como «HCl con pureza 37 %» daba un resultado distinto y penalizaba la pureza del producto; hay un test que fija la diferencia. `p/v` y `molar` necesitan la densidad **de la solución**. Concentraciones imposibles (más de 100 % en masa) se rechazan.

El modelo **no estima el efecto del solvente** (agua en una reacción sensible a la humedad, por ejemplo): solo avisa que el insumo está en solución.

### Densidades (`densidades.json`)

- Alcance: **líquidos puros a 20 °C**, 21 sustancias del catálogo.
- Fuentes: Perry's Chemical Engineers' Handbook 8.ª ed. (tabla 2-105), VDI Heat Atlas/PPDS y CRC Handbook, leídas a través de la librería `chemicals`.
- Regla: **solo se guarda un valor si al menos dos fuentes independientes coinciden** (tolerancia relativa 1,5 %). Las diferencias reales entre fuentes quedaron entre 0,05 % y 0,2 %.
- **13 sustancias quedaron sin dato** por no tener dos fuentes (por ejemplo isobutilbenceno, anilina, piridina). Para ellas hay que informar la densidad en cada ensayo. Figuran en la clave `sin_datos` con el motivo.
- Regenerar: `pip install -e ".[datos]" && python scripts/construir_densidades.py`.

## Incertidumbre (Monte Carlo)

Con `incertidumbre` en el pedido, la respuesta trae media, desvío y percentiles p5 / p50 / p95 de rendimiento, pureza, producto y puntaje, más la probabilidad de cumplir el mínimo de pureza.

- Perturba **la pesada** (desvío relativo, 0,5 % por defecto) y **la pureza de cada insumo** (0,5 puntos por defecto). Misma semilla ⇒ mismo resultado.
- Con réplicas (`rendimiento_replicas_pct`) se usa el promedio y el desvío de las réplicas.
- **Los desvíos por defecto son supuestos del analista, no datos.** Hay que reemplazarlos por la incertidumbre de la balanza y de cada certificado de análisis.
- **No cubre el error del modelo**: si el rendimiento y la pureza son estimaciones, el intervalo describe solo la propagación de errores de pesada y pureza, no cuánto se equivoca la estimación respecto del laboratorio. La respuesta lo dice en `notas` e `incluye_incertidumbre_del_modelo`. Solo se incluye ese error si el usuario informa `sd_rendimiento_pts` / `sd_pureza_producto_pts`.

## Origen de cada dato

Cada resultado indica de dónde sale cada número: `rendimiento_origen` y `pureza_origen` valen `modelo` o `experimental`, y `origen` resume: `estimacion` (todo del modelo), `mixto` o `medido` (rendimiento y pureza medidos). El estado de validación de la reacción viaja en el resultado y se imprime en los reportes. Mientras los parámetros no estén validados, **el rendimiento y la pureza medidos en el laboratorio son la única forma de obtener números confiables**.

## Especificación de varios parámetros

`data/especificaciones.json` define los parámetros de un producto. Reglas:

- El modelo solo **estima** la pureza (`modelado: true`). Los demás (pérdida por secado, residuo de ignición, metales pesados, sustancias relacionadas, solventes residuales) se cargan como **mediciones** del ensayo (`mediciones: {id: valor}`).
- Parámetro **sin límite cargado** ⇒ `sin_limite`: no se da por cumplido.
- Parámetro con límite pero **sin medición** ⇒ `sin_dato`: tampoco.
- El cumplimiento global es **«cumple» solo si todos los parámetros cumplen**; si falta algo, es **«incompleto»**, y si alguno falla, «no cumple».
- Para el ibuprofeno hoy hay un parámetro con límite (pureza mínima 98,5 %, **orientativo, no tomado de una farmacopea**) y cinco sin límite. **Los límites oficiales (USP, Ph. Eur., Farmacopea Argentina) tienen que cargarlos personas con acceso a la monografía vigente**; el programa no los inventa. Por eso ningún ensayo del ibuprofeno puede salir hoy como «cumple».
