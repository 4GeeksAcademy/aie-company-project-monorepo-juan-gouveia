"""POST /auth/login, GET /auth/me y la dependencia get_current_user."""

from datetime import timedelta

import pytest
from jose import jwt

from app.core.security import ALGORITHM, create_access_token
from app.domains.users import service
from app.domains.users.models import UserUpdate

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
PASSWORD = "parrilla-segura"


# --- Login -------------------------------------------------------------------------------


def test_login_with_json_returns_signed_jwt_with_user_id(api, make_user, auth_settings):
    user, _ = make_user()
    response = api.post(LOGIN, json={"email": "ana@brasaland.com", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(body["access_token"], auth_settings.secret_key, algorithms=[ALGORITHM])
    assert claims["sub"] == user.id
    assert claims["exp"] - claims["iat"] == 30 * 60


def test_login_with_form_used_by_docs_authorize_button(api, make_user):
    user, _ = make_user()
    response = api.post(LOGIN, data={"username": "ana@brasaland.com", "password": PASSWORD, "grant_type": "password"})
    assert response.status_code == 200
    assert api.get(ME, headers={"Authorization": f"Bearer {response.json()['access_token']}"}).json()["id"] == user.id


def test_login_email_is_case_insensitive(api, make_user):
    make_user()
    assert api.post(LOGIN, json={"email": " ANA@Brasaland.com ", "password": PASSWORD}).status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "ana@brasaland.com", "password": "otra-clave-cualquiera"},
        {"email": "nadie@brasaland.com", "password": PASSWORD},
    ],
)
def test_wrong_credentials_give_same_401(api, make_user, credentials):
    make_user()
    response = api.post(LOGIN, json=credentials)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"error": {"code": "invalid_credentials", "message": "Email o contraseña incorrectos."}}


def test_inactive_user_cannot_log_in(api, make_user, auth_store):
    user, _ = make_user()
    service.update_user(auth_store, user.id, UserUpdate(is_active=False))
    response = api.post(LOGIN, json={"email": "ana@brasaland.com", "password": PASSWORD})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inactive_user"


@pytest.mark.parametrize("payload", [{}, {"email": "ana@brasaland.com"}, {"password": PASSWORD}, {"email": "", "password": ""}])
def test_login_missing_fields_is_422(api, payload):
    response = api.post(LOGIN, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_login_invalid_json_is_422(api):
    response = api.post(LOGIN, content=b"{no es json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_login_other_content_type_is_415(api):
    response = api.post(LOGIN, content=b"ana:clave", headers={"Content-Type": "text/plain"})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_docs_describe_bearer_scheme_and_both_login_formats(api):
    schema = api.get("/openapi.json").json()
    scheme = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert scheme["flows"]["password"]["tokenUrl"] == LOGIN
    assert set(schema["paths"][LOGIN]["post"]["requestBody"]["content"]) == {
        "application/json",
        "application/x-www-form-urlencoded",
    }


# --- /auth/me y get_current_user -----------------------------------------------------------


def test_me_returns_email_role_and_profile(api, make_user):
    user, headers = make_user(name="Ana", phone="+57 300", address="Medellín")
    response = api.get(ME, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["email"], body["role"]) == (user.id, "ana@brasaland.com", "user")
    assert body["profile"]["name"] == "Ana"
    assert body["profile"]["phone"] == "+57 300"
    assert body["profile"]["address"] == "Medellín"
    assert "hashed_password" not in body


def test_token_from_login_works_on_protected_route(api, make_user):
    make_user()
    token = api.post(LOGIN, json={"email": "ana@brasaland.com", "password": PASSWORD}).json()["access_token"]
    assert api.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_me_without_token_is_401(api):
    response = api.get(ME)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "not_authenticated"


@pytest.mark.parametrize(
    "authorization",
    ["Bearer", "Bearer basura", "Bearer a.b.c", "Basic YW5hOmNsYXZl", "Token abc", "bearer x.y.z"],
)
def test_me_with_malformed_authorization_is_401(api, authorization):
    response = api.get(ME, headers={"Authorization": authorization})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_expired_token_is_401(api, make_user):
    user, _ = make_user()
    token = create_access_token(user.id, expires_delta=timedelta(seconds=-1))
    response = api.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


def test_me_with_token_signed_by_other_key_is_401(api, make_user):
    user, _ = make_user()
    token = jwt.encode({"sub": user.id, "iat": 0, "exp": 4_000_000_000}, "otra-clave-0123456789-0123456789", ALGORITHM)
    response = api.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_token_of_deleted_user_is_401(api, make_user, auth_store):
    user, headers = make_user()
    service.delete_user(auth_store, user.id)
    response = api.get(ME, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_token_of_deactivated_user_is_403(api, make_user, auth_store):
    user, headers = make_user()
    service.update_user(auth_store, user.id, UserUpdate(is_active=False))
    response = api.get(ME, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inactive_user"


def test_role_change_applies_without_new_token(api, make_user, auth_store):
    user, headers = make_user()
    service.update_user(auth_store, user.id, UserUpdate(role="manager"))
    assert api.get(ME, headers=headers).json()["role"] == "manager"
