import json
import os
import tempfile
from pathlib import Path

import pytest

# Las bases de pruebas van a archivos temporales, nunca a las reales.
_tmp = Path(tempfile.mkdtemp())
os.environ["SIM_DB_PATH"] = str(_tmp / "test.db")                       # catálogo (derivado de los JSON)
os.environ["SIM_DATABASE_URL"] = f"sqlite:///{_tmp / 'datos.db'}"       # usuarios, ensayos y auditoría
os.environ.pop("SIM_AUTH", None)

from app.core.simulador import cargar_reaccion  # noqa: E402
from app.models.schemas import ComponenteEntrada, Compuesto  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "app" / "data"


@pytest.fixture(scope="session")
def catalogo() -> dict[str, Compuesto]:
    with open(DATA / "compuestos.json", encoding="utf-8") as f:
        return {x["id"]: Compuesto.model_validate({**x, "pm": x.get("pm") or 0.0}) for x in json.load(f)}


@pytest.fixture(scope="session")
def reaccion():
    return cargar_reaccion()


@pytest.fixture
def mezcla_ejemplo() -> list[ComponenteEntrada]:
    """La misma mezcla del botón "Cargar ejemplo" de los prototipos."""
    return [
        ComponenteEntrada(id="ibb", gramos=134, pureza=99),
        ComponenteEntrada(id="aa", gramos=102, pureza=98),
        ComponenteEntrada(id="cat", gramos=20, pureza=97),
        ComponenteEntrada(id="h2", gramos=2, pureza=99),
        ComponenteEntrada(id="co", gramos=28, pureza=98),
        ComponenteEntrada(id="exc", gramos=30, pureza=99),
    ]
