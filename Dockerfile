# Etapa 1: compilar el frontend
FROM node:20-slim AS front
WORKDIR /f
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Etapa 2: backend + frontend compilado en un solo contenedor
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 SIM_STATIC_DIR=/app/static
WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/scripts ./scripts
RUN pip install --no-cache-dir ".[postgres]"
COPY --from=front /f/dist ./static
RUN useradd -r -u 10001 retorta && mkdir /datos && chown retorta /datos /app
USER retorta
# Base persistente: montar /datos como volumen (SQLite) o usar SIM_DATABASE_URL con PostgreSQL
ENV SIM_DATABASE_URL=sqlite:////datos/retorta_datos.db SIM_DB_PATH=/tmp/catalogo.db
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/salud')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
