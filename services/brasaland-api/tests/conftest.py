from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domains.incidents.dependencies import get_repository
from app.domains.incidents.repository import LastAnalysisRepository
from app.domains.suppliers.dependencies import get_repository as get_supplier_repository
from app.domains.suppliers.repository import SupplierRepository
from app.main import app

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "raw" / "incidents-brasaland.csv"


@pytest.fixture(autouse=True)
def supplier_repository(tmp_path):
    """Base TinyDB temporal en cada prueba: ninguna toca storage/brasaland-db.json.

    Es autouse porque el arranque de la API (lifespan) siembra proveedores, también en las
    pruebas de incidentes.
    """
    repository = SupplierRepository.from_path(tmp_path / "suppliers-test.json")
    app.dependency_overrides[get_supplier_repository] = lambda: repository
    yield repository
    app.dependency_overrides.pop(get_supplier_repository, None)
    repository.close()


@pytest.fixture
def client():
    """Cliente de pruebas con un almacén vacío, para que cada prueba empiece sin análisis previo."""
    repository = LastAnalysisRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_upload():
    """El CSV del briefing como archivo subido."""
    return {"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/csv")}
