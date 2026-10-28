# Supuestos del modelo

El motor (`backend/app/core/`) es un **modelo didáctico**. Sirve para explorar cómo cambian el rendimiento y la pureza al variar insumos, no para predecir resultados de laboratorio. Los parámetros viven en `backend/app/data/reacciones.json`; ninguno está validado.

## Varias reacciones

El motor no está atado al ibuprofeno: recibe una **reacción** (reactivos con su coeficiente, productos con su coeficiente y uno marcado como principal, catalizador y excipiente opcionales) y resuelve cualquier cantidad de reactivos y productos. Las reacciones están en `backend/app/data/reacciones.json` y deben conservar los átomos: el programa lo comprueba al arrancar y se niega a cargarlas si no.

Cada reacción puede sobreescribir los parámetros del modelo; los que no define usan los **genéricos del prototipo** (los mismos del ibuprofeno, sin validar). Dos diferencias respecto del ibuprofeno:

- Sin `catalizador_ratio_optimo` el catalizador no penaliza por cantidad. Si la reacción lo menciona y falta, solo se avisa (salvo `catalizador_requerido`, que mantiene la penalización del ibuprofeno).
- Si se informa un **rendimiento medido** en un ensayo real, reemplaza al estimado por el modelo y el resultado lo indica (`rendimiento_origen = "experimental"`). Es la forma de obtener números confiables hasta que los parámetros estén validados.

Además de lo anterior, para cualquier reacción se calcula: moles de cada reactivo, exceso de cada uno, gramos consumidos y sobrantes, gramos teóricos y estimados de **cada** producto, y economía atómica (masa del producto principal / masa de todos los reactivos según la ecuación).

## Cálculos que no dependen del catálogo

- **Peso molecular y composición porcentual** de cualquier fórmula (`/api/formulas/pm`): admite paréntesis, corchetes e hidratos.
- **Balanceo** de cualquier ecuación (`/api/estequiometria/balancear`): resuelve el sistema de conservación de átomos con aritmética exacta. Si la ecuación admite varias soluciones independientes (más especies que elementos + 1), lo avisa en lugar de elegir una.

## Reacción del ibuprofeno

Una reacción global simplificada con relación **1 : 1 : 1 : 1** entre isobutilbenceno, anhídrido acético, hidrógeno y monóxido de carbono, que da ibuprofeno (C₁₃H₁₈O₂, PM 206,28) **y ácido acético** como subproducto (con él, la ecuación conserva los átomos). El catalizador (AlCl₃) no se consume en el modelo.

> **Pendiente de revisar con una persona del área:** el prototipo mezcla elementos de más de una ruta de síntesis real (por ejemplo, el AlCl₃ es propio de la acilación de Friedel-Crafts, mientras que la secuencia acetilación → hidrogenación → carbonilación se parece más a una ruta de tres pasos). Hay que decidir qué ruta se modela y con qué coeficientes.

## Cálculos

1. **Moles útiles** = (gramos × pureza / 100) / PM. Se trabaja en moles; los gramos son solo entrada y salida.
2. **Reactivo limitante** = el de menores moles equivalentes (moles útiles / coeficiente).
3. **Rendimiento teórico (g)** = moles del limitante × PM del ibuprofeno.
4. **Factor de catalizador:** se compara la relación molar catalizador / limitante con un valor óptimo (0,15). Cuanto más se aleja, más baja el factor (pendiente 0,35, mínimo 0,4). Sin catalizador el factor es 0,5.
5. **Factor de exceso:** el exceso de cualquier reactivo sobre el limitante, por encima del 10 % tolerado, penaliza con pendiente 0,3 (mínimo 0,6).
6. **Rendimiento estimado** = mín(0,95, 0,85 × factor de catalizador × factor de exceso).
7. **Pureza del producto** = 100 − impureza media de los reactivos × 1,6 − (1 − factor de catalizador) × 4, acotada entre 80 y 99,9 %.
8. **% de principio activo** = ibuprofeno estimado / (ibuprofeno estimado + excipiente efectivo).
9. **Puntaje (0–100)** = 0,35 × rendimiento + 0,45 × pureza + 0,20 × balance estequiométrico, cada uno llevado a una escala de 0 a 100.

Categorías: Excelente ≥ 85, Buena ≥ 70, Regular ≥ 50, Deficiente < 50.

## Qué NO hace el modelo

- **No predice eficacia clínica.** El puntaje es de calidad de mezcla, no de efecto terapéutico.
- No modela cinética, temperatura, presión, tiempo, solvente ni pérdidas de purificación reales.
- No modela subproductos ni impurezas específicas (solo una impureza global a partir de la pureza de los insumos).
- No modela disolución, biodisponibilidad ni compatibilidad con excipientes.
- El mínimo de pureza (98,5 %) es **orientativo**: no está tomado de una farmacopea.

## Cómo se valida

Los tests (`backend/tests/test_simulador.py`) fijan que la mezcla de ejemplo dé 85 puntos (rendimiento 84,7 %, pureza 97,6 %) y que con 60 g de catalizador dé 56. Esos números son los del prototipo HTML, así que sirven para detectar cambios no intencionales, **no** para demostrar que el modelo es correcto químicamente.
