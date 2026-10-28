# Producto y despliegue

## Dos modos de funcionamiento

| | Modo local (por defecto) | Modo con login (`SIM_AUTH=on`) |
|---|---|---|
| Quién usa | una persona, en su equipo | varias personas con usuario y rol |
| Sesión | no hay; todo lo hace un administrador local («local@retorta») | token firmado, vence a las 8 h (`SIM_TOKEN_HORAS`) |
| Para qué sirve | probar, estudiar, desarrollo | uso compartido en un laboratorio |

El modo local **no es seguro para compartir**: cualquiera que llegue al puerto es administrador. Para más de una persona, usar `SIM_AUTH=on`.

## Roles

`lectura` < `analista` < `calidad` < `admin`.

- **lectura**: ve ensayos y reportes.
- **analista**: guarda ensayos, comenta y corrige los suyos.
- **calidad**: además revisa, aprueba o rechaza, corrige los de otros y ve la auditoría.
- **admin**: además administra usuarios.

Reglas del flujo: quien hizo el ensayo **no puede revisarlo, aprobarlo ni rechazarlo**; el estado avanza `registrado → revisado → aprobado` (o `rechazado`, que exige el motivo); un aprobado no vuelve atrás: se corrige con otro ensayo. Nunca se puede dejar el sistema sin un administrador activo.

## Ensayos: no se editan, no se borran

- El servidor **recalcula** el resultado con la mezcla recibida: no acepta un resultado de afuera.
- Se guarda con la **versión del modelo** (versión del programa + huella de los parámetros de la reacción y de las especificaciones) y una **huella SHA-256** del ensayo.
- Una mezcla incompleta (que no permite calcular) **no se guarda**.
- Corregir = guardar otro ensayo que lo reemplaza (`corrige_a`); el original queda intacto, marcado como reemplazado. Solo se corrige el último de la cadena.
- Importar los ensayos que la versión anterior guardaba en el navegador: el servidor los **recalcula** con el modelo actual y lo deja escrito en las notas; el resultado puede diferir del que se veía entonces.

## Auditoría

- Las tablas `ensayos`, `eventos` y `registro` **no admiten UPDATE, DELETE ni TRUNCATE** (disparadores en SQLite y PostgreSQL).
- `registro` es una **cadena de hashes** (cada fila incluye el hash de la anterior). Se registran altas de ensayos, comentarios y revisiones, altas y cambios de usuarios, y los ingresos (también los fallidos). **Nunca se guardan claves.**
- `GET /api/auditoria/verificar` recorre la cadena y detecta filas modificadas, borradas o agregadas por fuera de la aplicación, y ensayos que cambiaron después de registrarse.

**Alcance real:** es evidencia de alteración, **no una barrera contra quien administra la base**: esa persona podría desactivar los disparadores y reescribir toda la cadena. La defensa es guardar el último hash **fuera del sistema** (otro equipo, papel firmado) y compararlo después. Esto no cumple por sí solo con 21 CFR Part 11, Anexo 11 de GMP ni con exigencias de ANMAT; eso requiere validación del sistema (IQ/OQ/PQ), firmas electrónicas formales y procedimientos que dependen de la organización.

## Reportes

- `GET /api/ensayos/{id}/reporte.pdf` y `.xlsx`; `GET /api/ensayos/comparar.xlsx?ids=3,5,8`.
- El reporte siempre dice el **origen de los datos** (estimación / mixto / medido), el estado de validación del modelo, la especificación (incluida la palabra «incompleta») y la huella de trazabilidad. El PDF usa tipografía estándar: subíndices y flechas se escriben en texto plano.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `SIM_AUTH` | `on` exige login |
| `SIM_SECRET` | clave de firma de tokens, **32 caracteres o más**; con `SIM_AUTH=on` el servidor no arranca sin ella |
| `SIM_ADMIN_EMAIL`, `SIM_ADMIN_CLAVE` | crean el primer administrador si todavía no hay usuarios |
| `SIM_DATABASE_URL` | base persistente: `sqlite:///ruta.db` (por defecto) o `postgresql+psycopg://usuario:clave@host:5432/base` |
| `SIM_DB_PATH` | base derivada del catálogo (se rehace sola en cada arranque; no guarda nada del usuario) |
| `SIM_TOKEN_HORAS` | vigencia de la sesión (8 por defecto) |
| `SIM_CORS_ORIGINS` | orígenes permitidos, separados por coma |
| `SIM_STATIC_DIR` | carpeta del frontend compilado; si existe, el backend lo sirve en `/` |

Claves de usuario: 10 caracteres o más, con mayúsculas, minúsculas y un número; se guardan con scrypt y sal. Tras 5 intentos fallidos el ingreso de ese correo se bloquea 5 minutos (**el contador está en memoria**: se reinicia con el servidor y no se comparte entre varias réplicas).

## Docker

```bash
# .env (no subir al repositorio)
SIM_SECRET=...            # python -c "import secrets; print(secrets.token_urlsafe(48))"
SIM_ADMIN_EMAIL=admin@tu-laboratorio.com
SIM_ADMIN_CLAVE=...
POSTGRES_PASSWORD=...

docker compose up --build   # http://localhost:8000
```

Un solo contenedor sirve la API y el frontend compilado, con PostgreSQL aparte. Para un solo equipo sin PostgreSQL alcanza con `docker build` y montar `/datos`. **El Dockerfile y el compose no se pudieron construir en el entorno de desarrollo** (había cliente de Docker pero no el servicio que lo ejecuta). Sí se probó lo que ejecutan: el backend sirviendo el frontend compilado, el modo con login y PostgreSQL 16 real. Antes de usarlos, correr `docker compose up --build` una vez y verificar que arranca.

**Pendiente para producción real:** HTTPS (poner un proxy inverso con certificado delante), política de claves de la organización, monitoreo, y un plan de recuperación.

## Scripts

- `python scripts/crear_usuario.py correo "Nombre" rol` (clave por prompt o `SIM_NUEVA_CLAVE`).
- `python scripts/respaldo.py respaldar [carpeta]` (SQLite: copia consistente; PostgreSQL: `pg_dump`) y `verificar`. Imprime el último hash de la cadena: **guardarlo aparte**. Programar el respaldo (cron) y **probar una restauración** es responsabilidad de quien administre el servidor. El respaldo de PostgreSQL con `pg_dump` **no se probó** (solo el de SQLite).

## Pruebas

- Backend: `cd backend && pytest` (135 pruebas; con `SIM_TEST_POSTGRES_URL=postgresql+psycopg://...` se suman 16 de PostgreSQL).
- Interfaz: `cd frontend && npm install && npx playwright install chromium && npm run e2e` (17 pruebas; levantan backend y frontend solos con una base de prueba que se borra).
- CI: `.github/workflows/ci.yml` corre backend (con PostgreSQL), build del frontend y e2e. **Todavía no se ejecutó en GitHub**: se armó para correr lo mismo que se corrió a mano.

## Rendimiento medido

Con un catálogo sintético de **20 000 compuestos** (SQLite): una simulación tarda ~1,2 ms; una búsqueda paginada, ~23 ms; listar los 20 000 de una vez, ~0,35 s en la base. **Límite conocido:** el frontend todavía descarga el catálogo completo al abrir y filtra en el navegador; con miles de compuestos hay que pasar la búsqueda de la biblioteca al servidor (`?q=` ya existe en la API).
