"""`POST /auth/login`: la decisión de `issue_login_token` (token, 401 o 403) y las reglas de `LoginRequest`.

La lectura del cuerpo (JSON o formulario) es de la ruta y se prueba en `tests/integration/`.
"""

import pytest
from pydantic import ValidationError

from app.core.security import decode_access_token
from app.domains.auth.dependencies import BEARER_CHALLENGE
from app.domains.auth.router import issue_login_token
from app.domains.auth.schemas import LoginRequest
from tests.auth.helpers import PASSWORD, raises_api_error


def login(store, email: str, password: str):
    return issue_login_token(store, LoginRequest(email=email, password=password))


# --- Camino feliz ---------------------------------------------------------------------------


def test_log_f1_correct_credentials_issue_token_for_that_user(auth_store, active_user):
    token = login(auth_store, active_user.email, PASSWORD)

    assert token.token_type == "bearer"
    assert decode_access_token(token.access_token) == active_user.id


# --- Casos límite ---------------------------------------------------------------------------


@pytest.mark.parametrize("email", ["ANA@BRASALAND.COM", "  ana@brasaland.com  ", " Ana@Brasaland.com"])
def test_log_l1_email_case_and_surrounding_spaces_find_same_user(email, auth_store, active_user):
    token = login(auth_store, email, PASSWORD)

    assert decode_access_token(token.access_token) == active_user.id


@pytest.mark.parametrize("field", ["email", "password"])
def test_log_l2_empty_email_or_password_is_rejected_by_model(field):
    data = {"email": "ana@brasaland.com", "password": PASSWORD, field: ""}

    with pytest.raises(ValidationError) as info:
        LoginRequest(**data)
    assert [error["loc"] for error in info.value.errors()] == [(field,)]


def test_log_l3_password_over_72_bytes_is_invalid_credentials_not_error(auth_store, active_user):
    too_long = PASSWORD + "x" * 72

    with raises_api_error(401, "invalid_credentials"):
        login(auth_store, active_user.email, too_long)


# --- Modos de fallo -------------------------------------------------------------------------


def test_log_x1_wrong_password_and_unknown_email_get_identical_error(auth_store, active_user):
    with raises_api_error(401, "invalid_credentials") as wrong_password:
        login(auth_store, active_user.email, "no-es-la-contraseña")
    with raises_api_error(401, "invalid_credentials") as unknown_email:
        login(auth_store, "nadie@brasaland.com", PASSWORD)

    # Misma respuesta en los dos casos: no revela qué emails están registrados.
    assert wrong_password.value.message == unknown_email.value.message
    assert wrong_password.value.headers == unknown_email.value.headers == BEARER_CHALLENGE


def test_log_x2_inactive_account_with_correct_password_is_forbidden(auth_store, inactive_user):
    with raises_api_error(403, "inactive_user"):
        login(auth_store, inactive_user.email, PASSWORD)


def test_log_x3_inactive_account_with_wrong_password_does_not_reveal_status(auth_store, inactive_user):
    with raises_api_error(401, "invalid_credentials"):
        login(auth_store, inactive_user.email, "no-es-la-contraseña")
