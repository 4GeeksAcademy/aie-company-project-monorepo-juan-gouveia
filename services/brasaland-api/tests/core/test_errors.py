from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import ApiError, register_error_handlers


def make_client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/con-cabecera")
    def with_header():
        raise ApiError(401, "not_authenticated", "Inicia sesión.", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/sin-cabecera")
    def without_header():
        raise ApiError(404, "not_found", "No existe.")

    return TestClient(app)


def test_api_error_keeps_format_and_adds_headers():
    response = make_client().get("/con-cabecera")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"error": {"code": "not_authenticated", "message": "Inicia sesión."}}


def test_api_error_without_headers_is_unchanged():
    response = make_client().get("/sin-cabecera")
    assert response.status_code == 404
    assert "www-authenticate" not in response.headers
    assert response.json() == {"error": {"code": "not_found", "message": "No existe."}}


def test_framework_errors_keep_their_headers():
    # Un 405 de FastAPI conserva la cabecera Allow.
    response = make_client().post("/sin-cabecera")
    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert response.json()["error"]["code"] == "http_405"
