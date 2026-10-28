# Próximos pasos

## Antes de seguir construyendo
- [ ] Mostrar los prototipos (`prototipos/`) y recoger las respuestas de `preguntas-para-bioquimica.md`.
- [ ] Decidir el alcance: síntesis, formulación o ambas; educativo o profesional.
- [ ] Elegir la ruta de síntesis a modelar y corregir `data/reacciones.json` y `data/compuestos.json`.
- [ ] Reemplazar los parámetros inventados por valores con fuente (anotarlos en `fuentes-de-datos.md`).

## Interfaz
- [ ] Migrar la escena 3D de `prototipos/simulador-quimico-3d.html` a React con `three` / `@react-three/fiber`, reemplazando el esquema 2D del componente `Reactor`.
- [ ] Mostrar los parámetros del modelo (`GET /api/reaccion`) en un panel "Supuestos" para que se puedan auditar.
- [ ] Mostrar propiedades moleculares (`/api/compuestos/{id}/propiedades`) al elegir un compuesto.
- [ ] Pantalla para consultar la tabla periódica y la calculadora de fórmulas/balanceo (`/api/elementos`, `/api/formulas/pm`, `/api/estequiometria/balancear`).
- [ ] Buscador de la biblioteca contra la API (`?q=`) cuando el catálogo pase de unos cientos de compuestos; hoy se filtra en el navegador.

## Motor de cálculo
- [ ] Subproductos e impurezas específicas, no solo una impureza global.
- [ ] Rendimiento con condiciones configurables (temperatura, tiempo, pérdidas de purificación).
- [ ] Comparación contra especificaciones de farmacopea (varios parámetros, no solo pureza).
- [ ] Formulación: excipientes, tamaño de partícula, solubilidad y disolución estimada.
- [x] Más productos además del ibuprofeno (11 reacciones; estequiometría verificada, parámetros de rendimiento genéricos).
- [ ] Parámetros de rendimiento y pureza con fuente para cada reacción nueva.
- [ ] Reacciones de varios pasos (intermediarios) y rutas alternativas para un mismo producto.
- [ ] Concentración de soluciones (p. ej. HCl 37 %) como dato propio, no mezclada con la pureza.

## Catálogo de datos
- [ ] Verificar la lista RENPRE contra el Anexo II oficial y registrar en qué lista está cada sustancia.
- [ ] Que una persona del área revise la selección de sustancias y reacciones.
- [ ] Sumar sustancias: agregar a `scripts/semilla_catalogo.py` y correr `python scripts/construir_datos.py`.

## Infraestructura
- [ ] Migrar de SQLite a PostgreSQL si crece el catálogo.
- [ ] Tests de interfaz y CI.
- [ ] Empaquetado (Docker) para correr todo con un comando.
