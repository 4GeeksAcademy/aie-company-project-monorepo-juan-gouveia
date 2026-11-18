"""`POST /auth/reset-password/validate`: la ruta `validate_reset_token` y `passwords.check_reset_token`."""

from datetime import timedelta

import pytest

from app.core.security import create_access_token, create_password_reset_token
from app.domains.auth import passwords
from app.domains.auth.router import validate_reset_token
from app.domains.auth.schemas import ResetTokenCheck
from app.domains.users import service as user_service
from app.domains.users.models import UserUpdate
from tests.auth.helpers import NEW_PASSWORD, raises_api_error, request_reset

pytestmark = pytest.mark.anyio


async def validate(store, token: str):
    return await validate_reset_token(ResetTokenCheck(token=token), store=store)


# --- Camino feliz ---------------------------------------------------------------------------


async def test_val_f1_valid_link_is_accepted_and_not_consumed(auth_store, auth_settings, active_user, clock):
    reset, token = request_reset(auth_store, active_user, auth_settings, clock.now)

    await validate(auth_store, token)
    await validate(auth_store, token)

    assert auth_store.password_resets.get(reset.id).used_at is None
    # Sigue sirviendo para restablecer.
    passwords.reset_password(auth_store, token, NEW_PASSWORD, now=clock.now)


# --- Casos límite ---------------------------------------------------------------------------


def test_val_l1_link_valid_one_second_before_expiry_and_expired_at_exact_instant(
    auth_store, auth_settings, active_user, clock
):
    reset, token = request_reset(auth_store, active_user, auth_settings, clock.now)

    passwords.check_reset_token(auth_store, token, now=reset.expires_at - timedelta(seconds=1))

    with pytest.raises(passwords.ResetTokenError) as info:
        passwords.check_reset_token(auth_store, token, now=reset.expires_at)
    assert info.value.code == "reset_token_expired"


async def test_val_l1_link_past_jwt_expiry_is_expired(auth_store, auth_settings, active_user, clock):
    reset, token = request_reset(auth_store, active_user, auth_settings, clock.now)
    clock.advance(minutes=auth_settings.password_reset_expire_minutes, seconds=1)

    with raises_api_error(400, "reset_token_expired"):
        await validate(auth_store, token)


# --- Modos de fallo -------------------------------------------------------------------------


async def test_val_x1_used_link_is_reset_token_used(auth_store, auth_settings, active_user, clock):
    _, token = request_reset(auth_store, active_user, auth_settings, clock.now)
    passwords.reset_password(auth_store, token, NEW_PASSWORD, now=clock.now)

    with raises_api_error(400, "reset_token_used"):
        await validate(auth_store, token)


async def test_val_x1_text_that_is_not_a_token_is_invalid(auth_store):
    with raises_api_error(400, "invalid_reset_token"):
        await validate(auth_store, "no-es-un-token")


async def test_val_x1_access_token_is_not_a_reset_link(auth_store, active_user, clock):
    with raises_api_error(400, "invalid_reset_token"):
        await validate(auth_store, create_access_token(active_user.id, now=clock.now))


async def test_val_x2_token_pointing_to_another_users_link_is_invalid(
    auth_store, auth_settings, active_user, admin_user, clock
):
    other_reset, _ = request_reset(auth_store, admin_user, auth_settings, clock.now)
    forged = create_password_reset_token(
        active_user.id, other_reset.id, expires_at=other_reset.expires_at, now=clock.now
    )

    with raises_api_error(400, "invalid_reset_token"):
        await validate(auth_store, forged)


async def test_val_x2_token_with_unknown_link_id_is_invalid(auth_store, active_user, clock):
    forged = create_password_reset_token(
        active_user.id, "no-existe", expires_at=clock.now + timedelta(minutes=30), now=clock.now
    )

    with raises_api_error(400, "invalid_reset_token"):
        await validate(auth_store, forged)


async def test_val_x3_link_of_account_deactivated_afterwards_is_invalid(auth_store, auth_settings, active_user, clock):
    _, token = request_reset(auth_store, active_user, auth_settings, clock.now)
    user_service.update_user(auth_store, active_user.id, UserUpdate(is_active=False))

    with raises_api_error(400, "invalid_reset_token"):
        await validate(auth_store, token)


async def test_val_x3_link_of_deleted_account_is_invalid(auth_store, auth_settings, active_user, clock):
    _, token = request_reset(auth_store, active_user, auth_settings, clock.now)
    user_service.delete_user(auth_store, active_user.id)

    with raises_api_error(400, "invalid_reset_token"):
        await validate(auth_store, token)
