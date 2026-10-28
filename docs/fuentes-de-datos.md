# Fuentes de datos

Regla del proyecto: **cada dato tiene que tener fuente citada**. Hoy casi ninguno la tiene todavía; esta tabla es la lista de pendientes.

## Datos verificados

El catálogo se genera con `backend/scripts/construir_datos.py`, que **se detiene** si algún dato no cierra. Cada compuesto trae en `fuente` su CAS y su CID de PubChem.

| Dato | Cómo se verifica |
|---|---|
| Masas atómicas de los 118 elementos | Tomadas de la librería `periodictable` (datos NIST). En elementos sin isótopo estable es la masa del isótopo más estable conocido. |
| CAS ↔ fórmula de cada compuesto | La fórmula escrita en la semilla debe tener la misma composición que la que figura en la base pública (librería `chemicals`, identificadores de PubChem) para ese CAS. Además, el último dígito de cada CAS se comprueba como dígito de control (test). |
| Peso molecular de cada compuesto | **Calculado** a partir de la fórmula y las masas atómicas, y contrastado contra el de la base pública (tolerancia 0,06 g/mol). Coincide con los valores que tenía el prototipo (134,22 / 102,09 / 2,02 / 28,01 / 206,28). El del AlCl₃ da 133,33 en lugar de 133,34 por la masa del cloro que usa NIST; el efecto en el puntaje de ejemplo es nulo (sigue en 85). |
| Fase a 25 °C | Se deduce de los puntos de fusión y ebullición y se compara con la que figura en la semilla. |
| Estequiometría de cada reacción | El programa comprueba que la ecuación conserve los átomos (al arrancar y en los tests). |

### Limitaciones conocidas de esos datos

- Los puntos de fusión y ebullición salen de una base pública y **se descartaron los que no son confiables**: no se muestran los de descomposición o sublimación (p. ej. AlCl₃, CaCO₃, hidratos) ni la "ebullición" de sólidos orgánicos.
- Talco: la base pública lista una fórmula simplificada; se usa la del mineral (Mg₃Si₄O₁₀(OH)₂) y se marca `verificado = false`.
- Polímeros (celulosa, almidón, povidona): no tienen peso molecular único; no se pueden usar como reactivos, solo para el % de principio activo.
- El xileno se incluye como isómero *para* (CAS 106-42-3); el CAS de la mezcla (1330-20-7) no está en la base de verificación.

## Fiscalización (RENPRE)

| Dato | Fuente |
|---|---|
| Sustancias de las listas 1 y 2 (acetona, ácidos clorhídrico y sulfúrico, anhídrido acético, tolueno, permanganato de potasio, cloroformo, diclorometano, éter etílico, MEK, benzaldehído; acetato de etilo, ácido acético, amoníaco, carbonatos de sodio y potasio, hexano, hidróxidos de sodio y potasio, MIBK, sulfato de sodio, xilenos) | Certificado de inscripción RENPRE publicado por INCAPE-CONICET (https://incape.conicet.gov.ar/wp-content/uploads/sites/68/2024/11/Link-drogas-autorizadas-para-su-compra-RENPRE.pdf) |
| Ciclohexano y otras 24 sustancias de la lista III incorporadas en 2026 | Marval O'Farrell Mairal, 23/04/2026, sobre el Decreto 128/2026 (https://www.marval.com/Publicacion/precursores-quimicos-se-actualiza-el-listado-del-renpre-17568) |
| Umbral del 20 % p/v para HCl y amoníaco en solución | Presentación oficial del Ministerio de Seguridad (https://argentina.gob.ar/sites/default/files/consideraciones_generales_0.pdf) |

**Pendiente:** verificar contra el texto oficial del Anexo II del Decreto 593/2019 (y modificatorios) en el Boletín Oficial, y registrar en qué lista (I, II o III) está cada sustancia. Hoy el catálogo solo distingue "controlado" de "libre"; los certificados comerciales usan una numeración de listas que no se pudo cruzar con el texto del decreto.

| Dato | Valor | Cómo se verificó |
|---|---|---|
| Pesos moleculares del prototipo | 134,22 / 102,09 / 2,02 / 28,01 / 206,28 g/mol | Ahora se calculan desde la fórmula (ver arriba) y coinciden con los que tenían los datos del prototipo. |
| Fórmula del ibuprofeno | C₁₃H₁₈O₂ | Verificada contra el CAS 15687-27-1 en la base pública |

## Datos sin validar

| Dato | Dónde está | Estado |
|---|---|---|
| Relación estequiométrica 1:1:1:1 del ibuprofeno | `data/reacciones.json` | Es consistente (la ecuación global con ácido acético como subproducto conserva los átomos), pero resume una secuencia de pasos: a revisar con una persona del área |
| Parámetros de rendimiento y pureza de TODAS las reacciones nuevas | `data/reacciones.json` (sin sobreescrituras: usan los genéricos del prototipo) | Genéricos, **no validados**. Para un resultado real, usar el campo "rendimiento medido" |
| Relación óptima catalizador / limitante (0,15) y sus límites (0,08 y 0,30) | `data/reacciones.json` | Inventado para el prototipo |
| Rendimiento base 85 % y máximo 95 % | `data/reacciones.json` | Inventado para el prototipo |
| Penalizaciones por exceso e impurezas | `data/reacciones.json` | Inventadas para el prototipo |
| Mínimo de pureza 98,5 % | `data/especificaciones.json` | Orientativo; **falta** tomarlo de la monografía de la farmacopea que corresponda (USP, Ph. Eur., Farmacopea Argentina) |
| Excipiente: celulosa | `data/compuestos.json` | Sin PM único (es un polímero); la masa se usa solo para el % de principio activo |
| Selección de compuestos y reacciones del catálogo | `scripts/semilla_catalogo.py`, `data/reacciones.json` | Criterio editorial (ver `politica-de-sustancias.md`); una persona del área debería revisarlo |

## A conseguir

- Monografía oficial del ibuprofeno (límites de pureza, sustancias relacionadas, pérdida por secado, etc.).
- Datos de rendimiento y condiciones de la ruta de síntesis que se elija modelar.
- Propiedades experimentales (solubilidad, pKa, punto de fusión) con fuente, para contrastar con las estimadas por RDKit (el logP que da RDKit es una estimación por contribución de grupos).

> Pregunta para la bioquímica: ¿a qué farmacopeas y bases de datos tiene acceso para citar estos valores?
