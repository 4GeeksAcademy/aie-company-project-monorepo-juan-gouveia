from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domains.incidents.dependencies import get_repository
from app.domains.incidents.repository import LastAnalysisRepository
from app.main import app

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "raw" / "incidents-brasaland.csv"


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
