# Política de sustancias del catálogo

El catálogo es una **lista curada**, no una copia de una base de datos química entera. Cada sustancia entra porque una persona la agregó a `backend/scripts/semilla_catalogo.py`; el script solo completa y verifica sus datos.

## Qué entra

Sustancias de venta y uso legal en laboratorio, industria o farmacia: solventes, ácidos, bases, sales, gases industriales, elementos de uso común, principios activos de venta libre o de uso corriente y excipientes farmacéuticos.

## Qué no entra

- Estupefacientes y psicotrópicos (Ley 23.737 y convenios internacionales) y sus precursores directos.
- Explosivos, propelentes y sus precursores directos.
- Agentes de guerra química y sus precursores directos (Convención sobre Armas Químicas).
- Material radiactivo o nuclear. Los elementos radiactivos figuran en la tabla periódica (hace falta su masa atómica para calcular fórmulas) pero no se ofrecen como sustancias.

## Sustancias fiscalizadas (RENPRE)

En Argentina, el Registro Nacional de Precursores Químicos (Ley 26.045, Decreto 593/2019 y modificatorios) fiscaliza sustancias de uso industrial y farmacéutico corriente, como el anhídrido acético, la acetona o el ácido clorhídrico. **Sí entran al catálogo**, porque hay rutas legítimas que las necesitan (el anhídrido acético es parte de la síntesis de ibuprofeno), pero llevan:

- `acceso = "controlado"`
- un texto en `regulacion` que la interfaz muestra como aviso.

Estado de la verificación: solo están marcadas las sustancias que se pudieron comprobar en fuentes (ver `fuentes-de-datos.md`). **La ausencia de la marca no garantiza que una sustancia no esté fiscalizada.** Antes de operar con cualquier sustancia hay que consultar el Anexo II vigente y la normativa local. La lista cambia (por ejemplo, el Decreto 128/2026 incorporó 56 sustancias en marzo de 2026), así que conviene revisarla periódicamente.

Algunas sustancias se fiscalizan solo por encima de una concentración (el ácido clorhídrico y el amoníaco en solución, por encima del 20 % p/v). El catálogo lo indica en la nota del compuesto; el programa no calcula concentraciones.

## Qué es el programa y qué no

Es un simulador de **estimación**: calcula cantidades, proporciones y un puntaje a partir de un modelo. No da procedimientos, condiciones de operación ni instrucciones de síntesis, y no reemplaza ensayos de laboratorio ni el asesoramiento de un profesional.

El balanceo y el peso molecular funcionan con **cualquier fórmula** que se escriba (son aritmética), pero la simulación solo usa sustancias y reacciones del catálogo. Sumar una sustancia o una reacción es una decisión editorial que se hace en la semilla y en `reacciones.json`, y el programa rechaza las reacciones que no conservan los átomos.
