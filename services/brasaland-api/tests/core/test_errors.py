from datetime import date
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ValidationError

from app.core.errors import ApiError, describe_validation_errors, register_error_handlers


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
    assert response.json() == {"error": {"code": "http_405", "message": "Esta ruta no admite el método POST."}}


def test_unknown_route_answers_in_spanish():
    response = make_client().get("/no-existe")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "La ruta solicitada no existe. Revisa la URL."}}


class Sample(BaseModel):
    score: int = Field(ge=1, le=5)
    active: bool = True
    day: date | None = None
    code: str = Field("ABC", min_length=3)
    ref: UUID | None = None


def first_message(**data) -> str:
    with pytest.raises(ValidationError) as caught:
        Sample(**data)
    return describe_validation_errors(caught.value.errors())[0]["message"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"score": 0}, "Debe ser mayor o igual que 1."),
        ({"score": 9}, "Debe ser menor o igual que 5."),
        ({"score": 2.5}, "Debe ser un número entero, sin decimales."),
        ({"score": 3, "active": "quizás"}, "Debe ser verdadero o falso."),
        ({"score": 3, "day": "ayer"}, "Debe ser una fecha con el formato AAAA-MM-DD."),
        ({"score": 3, "code": "AB"}, "Debe tener al menos 3 caracteres."),
    ],
)
def test_validation_messages_are_in_spanish(data, message):
    assert first_message(**data) == message


def test_untranslated_validation_type_gets_generic_message():
    # uuid_parsing no está en la tabla: no se muestra el msg de Pydantic, en inglés.
    assert first_message(score=3, ref="no-es-uuid") == "El valor no es válido."

