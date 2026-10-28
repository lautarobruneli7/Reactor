# Simulador Químico (Retorta)

Simulador visual de formulación y calidad de productos químicos y farmacéuticos. El usuario elige una reacción, arma la mezcla (reactivos, catalizador, excipiente) en g, kg, mg, mL, L, mol o mmol —incluidas soluciones como HCl 37 % p/p—, y el programa calcula la estequiometría y estima rendimiento, pureza y un puntaje de calidad en tiempo real. Los ensayos se guardan en el servidor, con usuarios, revisión y aprobación, auditoría inalterable y reportes en PDF y Excel. El caso de partida es el **ibuprofeno**, pero el catálogo ya trae más de 130 sustancias, los 118 elementos y 11 reacciones, y los cálculos sirven para cualquier fórmula.

> **Alcance:** es una herramienta de **estimación**. El puntaje mide la calidad de la mezcla y del producto estimado (rendimiento, pureza, balance estequiométrico). **No mide eficacia clínica**. Todos los parámetros del modelo son supuestos didácticos **sin validar** (ver `docs/`): hasta contrastarlos con ensayos reales, los números que valen son el **rendimiento y la pureza medidos en el laboratorio**, que el programa permite cargar y distingue de los estimados en pantalla, reportes y auditoría. Una especificación incompleta (parámetros sin límite o sin medición) **nunca** se informa como «cumple».

## Estructura

```
simulador-quimico/
├── backend/                 API y motor de cálculo (Python + FastAPI)
│   ├── app/
│   │   ├── main.py          entrada de FastAPI
│   │   ├── config.py        variables de entorno (SIM_*)
│   │   ├── api/             rutas HTTP (compuestos, simulación, unidades, ensayos, usuarios, auditoría)
│   │   ├── core/            motor de cálculo y servicios
│   │   │   ├── simulador.py        orquesta estequiometría, pureza, formulación y calidad
│   │   │   ├── unidades.py         unidades, soluciones (%p/p, %p/v, molar) y densidades
│   │   │   ├── incertidumbre.py    Monte Carlo
│   │   │   ├── especificaciones.py especificación de varios parámetros
│   │   │   ├── servicio_ensayos.py ensayos, revisión, usuarios y auditoría
│   │   │   ├── auth.py             claves (scrypt), tokens firmados y roles
│   │   │   └── reportes.py         PDF y Excel
│   │   ├── models/          esquemas Pydantic
│   │   ├── db/              catálogo derivado (SQLite: database.py, seed.py) y datos persistentes (datos.py: SQLite o PostgreSQL)
│   │   └── data/            elementos, compuestos, reacciones, especificaciones y densidades (JSON)
│   ├── scripts/             catálogo y densidades verificados, crear_usuario.py, respaldo.py
│   └── tests/
├── frontend/                Interfaz (React + TypeScript + Vite), pruebas e2e con Playwright
├── prototipos/              Prototipos HTML de un solo archivo (2D y 3D)
├── Dockerfile, docker-compose.yml, .github/workflows/ci.yml
└── docs/                    Fuentes de datos, supuestos, producto y despliegue, próximos pasos
```

## Cómo correrlo

Necesitás **Python 3.10+** y **Node 18+**.

**1. Backend** (puerto 8000)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -e ".[dev,quimica]"    # "quimica" instala RDKit (opcional); "postgres" para usar PostgreSQL
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva de la API: <http://127.0.0.1:8000/docs>.

**2. Frontend** (puerto 5173), en otra terminal

```bash
cd frontend
npm install
npm run dev
```

Abrí <http://localhost:5173>. Tocá **Cargar ejemplo**: tiene que dar un puntaje de **85**.

Sin configurar nada corre en **modo local** (una persona, sin login). Para varias personas, usuarios y roles: `SIM_AUTH=on` con `SIM_SECRET` y el primer administrador; ver `docs/producto-y-despliegue.md`.

**3. Todo junto con Docker** (backend + frontend compilado + PostgreSQL): `docker compose up --build` con un `.env` (ver `docs/producto-y-despliegue.md`). *Escrito pero no ejecutado todavía.*

**4. Tests**

```bash
cd backend && pytest                                  # con SIM_TEST_POSTGRES_URL se suman las de PostgreSQL
cd frontend && npx playwright install chromium && npm run e2e   # pruebas de interfaz
```

## Aceptación de ensayos

La pestaña **Aceptación** (rol `calidad` o superior) es la cola de revisión: separa los ensayos **Por revisar**, **Por aprobar**, **Aprobados** y **Rechazados**, los pendientes de más antiguo a más nuevo, con un contador de pendientes en la pestaña. Cada ensayo muestra su resultado, su especificación, el origen de los datos (estimación / mixto / medido) y una lista «Antes de decidir»; desde ahí se comenta, se marca como revisado, se aprueba o se rechaza (el rechazo exige el motivo) y el panel pasa al siguiente.

Reglas (las hace cumplir el servidor, no la pantalla): quien hizo el ensayo no puede revisarlo ni decidirlo; el flujo es `registrado → revisado → aprobado` o `rechazado`; un ensayo reemplazado no se revisa. El estado no es una columna: se deduce de los eventos inalterables, por eso este panel no cambió el esquema de la base. Aprobar un ensayo cuya especificación no cumple pide una justificación **solo en la interfaz** (el servidor todavía no lo exige).

Para probar el flujo hacen falta dos personas distintas de calidad: arrancar con `SIM_AUTH=on` (ver `docs/producto-y-despliegue.md`) y crear dos usuarios.

## API

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/salud`, `/api/sistema` | Estado del servicio, versión y si hay login |
| GET | `/api/compuestos` | Catálogo, con `q`, `categoria`, `fase`, `acceso`, `tipo`, `limit` y `offset`. El total va en `X-Total-Count` |
| GET | `/api/compuestos/{id}`, `/propiedades`, `/densidad` | Un compuesto, sus propiedades (RDKit) y su densidad (si hay dato confiable) |
| GET | `/api/categorias`, `/api/elementos` | Categorías de la biblioteca y tabla periódica (118 elementos, masas NIST) |
| GET | `/api/formulas/pm?formula=…` | Peso molecular y composición de **cualquier** fórmula |
| POST | `/api/estequiometria/balancear` | Balancea una ecuación |
| POST | `/api/unidades/convertir`, `/api/soluciones/convertir` | Conversión de cantidades y de concentraciones |
| GET | `/api/reacciones`, `/api/reacciones/{id}`, `/api/especificaciones` | Reacciones y especificaciones cargadas |
| POST | `/api/simulacion` | Simula una mezcla. Admite `cantidad`+`unidad`, `concentracion`, `rendimiento_real_pct` o `rendimiento_replicas_pct`, `pureza_real_pct`, `mediciones` e `incertidumbre` |
| POST | `/api/auth/login`, GET `/api/auth/yo`, `/api/usuarios` | Sesión y administración de usuarios (con `SIM_AUTH=on`) |
| POST/GET | `/api/ensayos`, `/api/ensayos/{id}` | Guarda (el servidor recalcula) y consulta ensayos. El listado admite `orden=recientes\|antiguos` |
| GET | `/api/ensayos/conteo` | Cantidad de ensayos por estado (registrado, revisado, aprobado, rechazado, reemplazados) |
| POST | `/api/ensayos/{id}/corregir`, `/eventos` | Corrección por reemplazo; comentarios, revisión, aprobación y rechazo |
| GET | `/api/ensayos/{id}/reporte.pdf`, `.xlsx`, `/api/ensayos/comparar(.xlsx)?ids=` | Reportes y comparación |
| GET | `/api/auditoria`, `/api/auditoria/verificar` | Registro y verificación de integridad (rol calidad) |

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/api/simulacion \
  -H "Content-Type: application/json" \
  -d '{"componentes":[{"id":"ibb","gramos":134,"pureza":99},{"id":"aa","gramos":102,"pureza":98},{"id":"cat","gramos":20,"pureza":97},{"id":"h2","gramos":2,"pureza":99},{"id":"co","gramos":28,"pureza":98},{"id":"exc","gramos":30,"pureza":99}]}'
```

## Catálogo de datos

El catálogo vive en `backend/app/data/` y se regenera con scripts que **verifican cada dato** antes de guardarlo (CAS contra fórmula, peso molecular calculado contra la base pública, fase contra puntos de fusión y ebullición; densidades solo con dos fuentes que coinciden):

```bash
pip install -e ".[datos]"
python scripts/construir_datos.py
python scripts/construir_densidades.py
```

La lista de sustancias la define una persona en `backend/scripts/semilla_catalogo.py` (reglas en `docs/politica-de-sustancias.md`). Al arrancar, el backend valida todo (incluido que cada reacción conserve los átomos) y rehace la base SQLite del catálogo; si algo está mal, no arranca. **Los usuarios, ensayos y la auditoría están en otra base** (`SIM_DATABASE_URL`) que nunca se rehace: hay que respaldarla (`scripts/respaldo.py`).

## Prototipos

En `prototipos/` hay dos archivos HTML autónomos (doble clic, sin instalar nada): la primera versión 2D y la versión 3D que sirvió de referencia visual. El motor del backend reproduce los números de estos prototipos (hay tests que lo comprueban).

## Documentación

- `docs/supuestos-del-modelo.md`: cómo se calcula cada cosa y qué simplifica.
- `docs/unidades-incertidumbre-y-especificaciones.md`: unidades, soluciones, densidades, Monte Carlo y especificaciones, con sus límites.
- `docs/producto-y-despliegue.md`: usuarios, roles, ensayos, auditoría, reportes, variables de entorno, Docker, respaldos y rendimiento medido.
- `docs/fuentes-de-datos.md`: de dónde sale cada dato y su estado de validación.
- `docs/politica-de-sustancias.md`: qué sustancias entran, cuáles no y cómo se marcan las fiscalizadas.
- `docs/preguntas-para-bioquimica.md`: preguntas para validar el enfoque con una persona del área.
- `docs/proximos-pasos.md`: qué está hecho, qué no se resuelve programando y qué falta.
