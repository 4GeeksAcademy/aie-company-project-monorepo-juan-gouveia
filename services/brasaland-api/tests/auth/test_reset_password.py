"""`POST /auth/reset-password`: la ruta `reset_password`, `passwords.reset_password` y `ResetPasswordRequest`."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.core.security import create_access_token, create_password_reset_token
from app.domains.auth import passwords
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.router import reset_password
from app.domains.auth.schemas import ResetPasswordRequest
from app.domains.users import service as user_service
from tests.auth.helpers import NEW_PASSWORD, PASSWORD, raises_api_error, request_reset

pytestmark = pytest.mark.anyio


async def reset(store, token: str, new_password: str = NEW_PASSWORD):
    return await reset_password(ResetPasswordRequest(token=token, new_password=new_password), store=store)


def assert_password_unchanged(store, user):
    assert user_service.authenticate_user(store, user.email, PASSWORD) is not None
    assert store.users.get(user.id).password_changed_at is None


# --- Camino feliz ---------------------------------------------------------------------------


async def test_rst_f1_new_password_works_link_used_and_old_sessions_revoked(
    auth_store, auth_settings, active_user, clock
):
    old_session = create_access_token(active_user.id, now=clock.ago(seconds=5))
    link, token = request_reset(auth_store, active_user, auth_settings, clock.now)

    await reset(auth_store, token)

    assert user_service.authenticate_user(auth_store, active_user.email, NEW_PASSWORD) is not None
    assert user_service.authenticate_user(auth_store, active_user.email, PASSWORD) is None
    assert auth_store.password_resets.get(link.id).used_at is not None
    assert auth_store.users.get(active_user.id).password_changed_at is not None
    with raises_api_error(401, "session_revoked"):
        get_current_user(token=old_session, store=auth_store)


# --- Casos límite ---------------------------------------------------------------------------


async def test_rst_l1_using_one_link_cancels_the_other_pending_one(auth_store, auth_settings, active_user, clock):
    _, first = request_reset(auth_store, active_user, auth_settings, clock.now)
    second_link, second = request_reset(auth_store, active_user, auth_settings, clock.now)

    await reset(auth_store, first)

    assert auth_store.password_resets.get(second_link.id).used_at is not None
    with raises_api_error(400, "reset_token_used"):
        await reset(auth_store, second, "otra-contraseña-nueva")


@pytest.mark.parametrize(
    "new_password",
    ["a" * 8, "á" * 36],  # 8 caracteres; 72 bytes (cada "á" ocupa 2 en UTF-8)
    ids=["8-caracteres", "72-bytes"],
)
def test_rst_l2_password_at_the_limits_is_accepted(new_password):
    assert ResetPasswordRequest(token="t", new_password=new_password).new_password == new_password


@pytest.mark.parametrize(
    "new_password",
    ["a" * 7, "á" * 36 + "a"],  # 7 caracteres; 73 bytes con solo 37 caracteres
    ids=["7-caracteres", "73-bytes"],
)
def test_rst_l2_password_past_the_limits_is_rejected(new_password):
    with pytest.raises(ValidationError) as info:
        ResetPasswordRequest(token="t", new_password=new_password)
    assert [error["loc"] for error in info.value.errors()] == [("new_password",)]


async def test_rst_l2_72_byte_password_is_usable_to_log_in(auth_store, auth_settings, active_user, clock):
    _, token = request_reset(auth_store, active_user, auth_settings, clock.now)

    await reset(auth_store, token, "á" * 36)

    assert user_service.authenticate_user(auth_store, active_user.email, "á" * 36) is not None


# --- Modos de fallo -------------------------------------------------------------------------


async def test_rst_x1_used_link_fails_and_keeps_the_newer_password(auth_store, auth_settings, active_user, clock):
    _, token = request_reset(auth_store, active_user, auth_settings, clock.now)
    await reset(auth_store, token)

    with raises_api_error(400, "reset_token_used"):
        await reset(auth_store, token, "intento-de-reutilizar")
    assert user_service.authenticate_user(auth_store, active_user.email, NEW_PASSWORD) is not None


def test_rst_x1_link_expired_in_store_fails_without_changing_password(auth_store, auth_settings, active_user, clock):
    link, token = request_reset(auth_store, active_user, auth_settings, clock.now)

    with pytest.raises(passwords.ResetTokenError) as info:
        passwords.reset_password(auth_store, token, NEW_PASSWORD, now=link.expires_at)

    assert info.value.code == "reset_token_expired"
    assert auth_store.password_resets.get(link.id).used_at is None
    assert_password_unchanged(auth_store, active_user)


async def test_rst_x1_link_with_expired_jwt_fails_without_changing_password(
    auth_store, auth_settings, active_user, clock
):
    link, token = request_reset(auth_store, active_user, auth_settings, clock.now)
    clock.advance(minutes=auth_settings.password_reset_expire_minutes, seconds=1)

    with raises_api_error(400, "reset_token_expired"):
        await reset(auth_store, token)
    assert_password_unchanged(auth_store, active_user)


@pytest.mark.parametrize("kind", ["texto", "token de acceso", "enlace inexistente"])
async def test_rst_x1_invalid_link_fails_without_changing_password(kind, auth_store, active_user, clock):
    token = {
        "texto": "no-es-un-token",
        "token de acceso": create_access_token(active_user.id, now=clock.now),
        "enlace inexistente": create_password_reset_token(
            active_user.id, "no-existe", expires_at=clock.now + timedelta(minutes=30), now=clock.now
        ),
    }[kind]

    with raises_api_error(400, "invalid_reset_token"):
        await reset(auth_store, token)
    assert_password_unchanged(auth_store, active_user)
