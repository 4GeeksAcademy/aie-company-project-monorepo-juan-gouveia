"""Restablecimiento y cambio de contraseña (ticket AUTH-03): /auth/forgot-password,
/auth/reset-password y /auth/change-password."""

import re
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.email import EmailMessage, get_email_sender
from app.core.security import ALGORITHM, create_access_token, create_password_reset_token
from app.domains.auth import passwords
from app.domains.auth.schemas import FORGOT_PASSWORD_MESSAGE
from app.domains.users import service as user_service
from app.domains.users.models import UserUpdate
from app.main import app

FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"
VALIDATE = "/api/v1/auth/reset-password/validate"
CHANGE = "/api/v1/auth/change-password"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"

EMAIL = "ana@brasaland.com"
OLD_PASSWORD = "parrilla-segura"
NEW_PASSWORD = "brasas-nuevas-2026"


def token_from(message: EmailMessage) -> str:
    match = re.search(r"/reset-password\?token=(\S+)", message.text)
    assert match, message.text
    return match.group(1)


def earlier_session(user_id: str) -> dict:
    """Token emitido unos segundos antes, como una sesión abierta antes del cambio de contraseña.

    `iat` va en segundos enteros: un token del mismo segundo que el cambio sigue valiendo (así vale
    el token nuevo que devuelve change-password). Ver test_tokens_from_the_same_second_...
    """
    issued = datetime.now(timezone.utc) - timedelta(seconds=5)
    return {"Authorization": f"Bearer {create_access_token(user_id, now=issued)}"}


def login(api, password: str, email: str = EMAIL):
    return api.post(LOGIN, json={"email": email, "password": password})


@pytest.fixture
def user(make_user):
    created, headers = make_user(EMAIL, name="Ana Gómez")
    return created, headers


@pytest.fixture
def reset_token(api, user, email_sender) -> str:
    api.post(FORGOT, json={"email": EMAIL})
    return token_from(email_sender.sent[-1])


# --- forgot-password ---------------------------------------------------------------------------


def test_forgot_password_sends_the_link_to_a_registered_email(api, user, email_sender):
    response = api.post(FORGOT, json={"email": EMAIL})
    assert response.status_code == 200
    assert response.json() == {"message": FORGOT_PASSWORD_MESSAGE}

    (message,) = email_sender.sent
    assert message.to == EMAIL
    link = f"{get_settings().frontend_url}/reset-password?token="
    assert link in message.text and link in message.html
    assert "Ana Gómez" in message.text
    assert "30 minutos" in message.text


def test_forgot_password_normalizes_the_email(api, user, email_sender):
    assert api.post(FORGOT, json={"email": "  ANA@Brasaland.com "}).status_code == 200
    assert len(email_sender.sent) == 1


@pytest.mark.parametrize("email", ["nadie@brasaland.com", "otra@example.org"])
def test_forgot_password_answers_the_same_for_unknown_emails(api, user, email_sender, email):
    known = api.post(FORGOT, json={"email": EMAIL})
    unknown = api.post(FORGOT, json={"email": email})
    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()
    assert [message.to for message in email_sender.sent] == [EMAIL]


def test_forgot_password_sends_nothing_to_an_inactive_account(api, user, auth_store, email_sender):
    user_service.update_user(auth_store, user[0].id, UserUpdate(is_active=False))
    response = api.post(FORGOT, json={"email": EMAIL})
    assert response.status_code == 200
    assert response.json() == {"message": FORGOT_PASSWORD_MESSAGE}
    assert email_sender.sent == []


def test_forgot_password_limits_requests_per_hour_without_revealing_it(api, user, email_sender):
    responses = [api.post(FORGOT, json={"email": EMAIL}) for _ in range(passwords.MAX_RESET_REQUESTS_PER_HOUR + 2)]
    assert {response.status_code for response in responses} == {200}
    assert len({response.text for response in responses}) == 1
    assert len(email_sender.sent) == passwords.MAX_RESET_REQUESTS_PER_HOUR


def test_old_requests_do_not_count_towards_the_limit(api, user, auth_store, email_sender):
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    for _ in range(passwords.MAX_RESET_REQUESTS_PER_HOUR):
        passwords.request_password_reset(auth_store, EMAIL, get_settings(), now=two_hours_ago)
    api.post(FORGOT, json={"email": EMAIL})
    assert len(email_sender.sent) == 1


def test_forgot_password_still_answers_200_when_the_email_provider_fails(api, user):
    class FailingSender:
        def send(self, message):
            raise RuntimeError("403 You can only send testing emails to your own email address")

    app.dependency_overrides[get_email_sender] = lambda: FailingSender()
    response = api.post(FORGOT, json={"email": EMAIL})
    assert response.status_code == 200
    assert response.json() == {"message": FORGOT_PASSWORD_MESSAGE}


@pytest.mark.parametrize("body", [{}, {"email": "no-es-un-email"}, {"email": EMAIL, "extra": 1}])
def test_forgot_password_rejects_invalid_bodies(api, body):
    response = api.post(FORGOT, json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_reset_link_uses_frontend_url(api, user, email_sender, monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://backoffice.brasaland.test/")
    get_settings.cache_clear()
    api.post(FORGOT, json={"email": EMAIL})
    assert "https://backoffice.brasaland.test/reset-password?token=" in email_sender.sent[0].text


# --- reset-password ----------------------------------------------------------------------------


def test_reset_password_changes_the_password(api, reset_token):
    response = api.post(RESET, json={"token": reset_token, "new_password": NEW_PASSWORD})
    assert response.status_code == 200
    assert login(api, NEW_PASSWORD).status_code == 200
    assert login(api, OLD_PASSWORD).status_code == 401


def test_reset_token_cannot_be_used_twice(api, reset_token):
    assert api.post(RESET, json={"token": reset_token, "new_password": NEW_PASSWORD}).status_code == 200
    again = api.post(RESET, json={"token": reset_token, "new_password": "otra-clave-distinta"})
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "reset_token_used"
    assert login(api, NEW_PASSWORD).status_code == 200


def test_using_one_link_invalidates_the_other_pending_links(api, user, email_sender):
    api.post(FORGOT, json={"email": EMAIL})
    api.post(FORGOT, json={"email": EMAIL})
    first, second = (token_from(message) for message in email_sender.sent)
    assert api.post(RESET, json={"token": second, "new_password": NEW_PASSWORD}).status_code == 200
    response = api.post(RESET, json={"token": first, "new_password": "otra-clave-distinta"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "reset_token_used"


def test_expired_reset_token_is_rejected(api, user, auth_store):
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    request = passwords.request_password_reset(auth_store, EMAIL, get_settings(), now=past)
    response = api.post(RESET, json={"token": token_from(request.message), "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "reset_token_expired"
    assert login(api, OLD_PASSWORD).status_code == 200


def test_token_expires_after_the_configured_window(api, user, auth_store, monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_EXPIRE_MINUTES", "15")
    get_settings.cache_clear()
    sixteen_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=16)
    request = passwords.request_password_reset(auth_store, EMAIL, get_settings(), now=sixteen_minutes_ago)
    response = api.post(RESET, json={"token": token_from(request.message), "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "reset_token_expired"


@pytest.mark.parametrize("token", ["basura", "a.b.c"])
def test_malformed_reset_token_is_rejected(api, user, token):
    response = api.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_reset_token"


def test_access_token_is_not_a_reset_token(api, user):
    access_token = create_access_token(user[0].id)
    response = api.post(RESET, json={"token": access_token, "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_reset_token"


def test_signed_reset_token_without_a_stored_link_is_rejected(api, user):
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    forged = create_password_reset_token(user[0].id, "jti-que-no-existe", expires_at=expires)
    response = api.post(RESET, json={"token": forged, "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_reset_token"


def test_reset_token_signed_with_another_key_is_rejected(api, user, reset_token):
    claims = jwt.get_unverified_claims(reset_token)
    forged = jwt.encode(claims, "otra-clave-0123456789-0123456789", ALGORITHM)
    response = api.post(RESET, json={"token": forged, "new_password": NEW_PASSWORD})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_reset_token"


def test_reset_token_cannot_be_used_as_a_session(api, reset_token):
    response = api.get(ME, headers={"Authorization": f"Bearer {reset_token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


@pytest.mark.parametrize("password", ["corta", "x" * 73])
def test_reset_password_applies_the_password_rules(api, reset_token, password):
    response = api.post(RESET, json={"token": reset_token, "new_password": password})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "new_password"


def test_reset_password_closes_existing_sessions(api, user, reset_token):
    old_headers = earlier_session(user[0].id)
    assert api.get(ME, headers=old_headers).status_code == 200
    api.post(RESET, json={"token": reset_token, "new_password": NEW_PASSWORD})
    response = api.get(ME, headers=old_headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_revoked"
    new_token = login(api, NEW_PASSWORD).json()["access_token"]
    assert api.get(ME, headers={"Authorization": f"Bearer {new_token}"}).status_code == 200


def test_reset_password_is_stored_as_a_hash(api, reset_token, tmp_path):
    api.post(RESET, json={"token": reset_token, "new_password": NEW_PASSWORD})
    raw = (tmp_path / "auth-test.json").read_text(encoding="utf-8")
    assert NEW_PASSWORD not in raw
    assert reset_token not in raw


# --- reset-password/validate ------------------------------------------------------------------


def test_validate_accepts_a_pending_link_without_using_it(api, reset_token):
    assert api.post(VALIDATE, json={"token": reset_token}).status_code == 200
    assert api.post(VALIDATE, json={"token": reset_token}).status_code == 200
    # Sigue sirviendo para restablecer.
    assert api.post(RESET, json={"token": reset_token, "new_password": NEW_PASSWORD}).status_code == 200


def test_validate_reports_a_used_link(api, reset_token):
    api.post(RESET, json={"token": reset_token, "new_password": NEW_PASSWORD})
    response = api.post(VALIDATE, json={"token": reset_token})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "reset_token_used"


def test_validate_reports_an_expired_link(api, user, auth_store):
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    request = passwords.request_password_reset(auth_store, EMAIL, get_settings(), now=past)
    response = api.post(VALIDATE, json={"token": token_from(request.message)})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "reset_token_expired"


@pytest.mark.parametrize("token", ["basura", "a.b.c"])
def test_validate_reports_an_invalid_link(api, user, token):
    response = api.post(VALIDATE, json={"token": token})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_reset_token"


def test_validate_rejects_an_access_token(api, user):
    response = api.post(VALIDATE, json={"token": create_access_token(user[0].id)})
    assert response.status_code == 400


def test_validate_requires_a_token(api):
    assert api.post(VALIDATE, json={}).status_code == 422


# --- change-password ---------------------------------------------------------------------------


def test_change_password_requires_a_session(api, user):
    response = api.post(CHANGE, json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD})
    assert response.status_code == 401


def test_change_password_rejects_a_wrong_current_password(api, user):
    _, headers = user
    response = api.post(
        CHANGE, json={"current_password": "no-es-la-actual", "new_password": NEW_PASSWORD}, headers=headers
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_current_password"
    assert login(api, OLD_PASSWORD).status_code == 200
    # La sesión no se cierra por equivocarse de contraseña.
    assert api.get(ME, headers=headers).status_code == 200


def test_change_password_returns_a_new_token_and_closes_other_sessions(api, user):
    _, headers = user
    old_headers = earlier_session(user[0].id)
    response = api.post(
        CHANGE, json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer" and body["message"] == "Contraseña actualizada."

    assert api.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"}).status_code == 200
    # Otra sesión abierta antes del cambio (otro dispositivo) deja de valer.
    old = api.get(ME, headers=old_headers)
    assert old.status_code == 401
    assert old.json()["error"]["code"] == "session_revoked"
    assert login(api, NEW_PASSWORD).status_code == 200
    assert login(api, OLD_PASSWORD).status_code == 401


def test_change_password_invalidates_pending_reset_links(api, user, reset_token):
    _, headers = user
    api.post(CHANGE, json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD}, headers=headers)
    response = api.post(RESET, json={"token": reset_token, "new_password": "otra-clave-distinta"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "reset_token_used"


@pytest.mark.parametrize(
    "body",
    [
        {"current_password": OLD_PASSWORD, "new_password": "corta"},
        {"current_password": "", "new_password": NEW_PASSWORD},
        {"new_password": NEW_PASSWORD},
    ],
)
def test_change_password_validates_the_body(api, user, body):
    _, headers = user
    assert api.post(CHANGE, json=body, headers=headers).status_code == 422


# --- revocación de sesiones --------------------------------------------------------------------


def test_tokens_from_the_same_second_as_the_change_still_work(user):
    created, _ = user
    changed = datetime(2026, 11, 6, 10, 0, 0, tzinfo=timezone.utc)
    changed_user = created.model_copy(update={"password_changed_at": changed})
    assert passwords.is_token_revoked(changed_user, int(changed.timestamp()) - 1)
    assert not passwords.is_token_revoked(changed_user, int(changed.timestamp()))
    assert not passwords.is_token_revoked(created, 0)
