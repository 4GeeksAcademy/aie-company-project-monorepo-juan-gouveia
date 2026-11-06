from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.email import EmailMessage, get_email_sender
from app.core.security import create_access_token
from app.domains.users import service as user_service
from app.domains.users.models import Role, UserCreate
from app.domains.incidents.dependencies import get_repository
from app.domains.incidents.repository import LastAnalysisRepository
from app.domains.suppliers.dependencies import get_repository as get_supplier_repository
from app.domains.suppliers.repository import SupplierRepository
from app.domains.users.database import AuthStore
from app.domains.users.dependencies import get_auth_store
from app.main import app

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "raw" / "incidents-brasaland.csv"


TEST_SECRET_KEY = "clave-de-pruebas-solo-para-pytest-0123456789"


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch):
    """Configuración de pruebas: no depende del .env local ni de las variables del sistema."""
    monkeypatch.setenv("SECRET_KEY", TEST_SECRET_KEY)
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


class FakeEmailSender:
    """Guarda los mensajes en vez de enviarlos: ninguna prueba llama a Resend."""

    def __init__(self):
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.fixture(autouse=True)
def email_sender():
    """Emisor de correo falso en todas las pruebas (AUTH-03); `email_sender.sent` tiene lo enviado."""
    sender = FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    yield sender
    app.dependency_overrides.pop(get_email_sender, None)


@pytest.fixture(autouse=True)
def auth_store(tmp_path):
    """Base TinyDB temporal de usuarios y perfiles: ninguna prueba toca storage/auth-db.json."""
    store = AuthStore.from_path(tmp_path / "auth-test.json")
    app.dependency_overrides[get_auth_store] = lambda: store
    yield store
    app.dependency_overrides.pop(get_auth_store, None)
    store.close()


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
def client(auth_headers):
    """Cliente de incidentes con un almacén vacío y el token de un usuario autenticado.

    Las rutas de incidentes exigen token (AUTH-01): así las pruebas comprueban su comportamiento
    con una sesión válida.
    """
    repository = LastAnalysisRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app, headers=auth_headers) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def api():
    """Cliente de la API sin token, sobre las bases temporales de los fixtures autouse."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(auth_store):
    """Crea un usuario y devuelve (usuario, cabeceras con su token). Por defecto, rol `user`."""

    def factory(email: str = "ana@brasaland.com", role: Role = Role.USER, password: str = "parrilla-segura", **profile):
        user, _ = user_service.create_user(auth_store, UserCreate(email=email, password=password, **profile), role=role)
        return user, {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return factory


@pytest.fixture
def auth_headers(make_user):
    """Cabeceras con el token de un usuario normal (rol `user`), para llamar a rutas protegidas."""
    _, headers = make_user("equipo@brasaland.com")
    return headers


@pytest.fixture
def sample_upload():
    """El CSV del briefing como archivo subido."""
    return {"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/csv")}
