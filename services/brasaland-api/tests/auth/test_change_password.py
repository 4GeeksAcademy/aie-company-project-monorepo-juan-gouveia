"""`POST /auth/change-password`: la ruta `change_password` y `ChangePasswordRequest`."""

import pytest
from pydantic import ValidationError

from app.core.security import create_access_token, decode_access_token
from app.domains.auth import passwords
from app.domains.auth.dependencies import BEARER_CHALLENGE, get_current_user
from app.domains.auth.router import change_password
from app.domains.auth.schemas import ChangePasswordRequest
from app.domains.users import service as user_service
from tests.auth.helpers import NEW_PASSWORD, PASSWORD, raises_api_error, request_reset

pytestmark = pytest.mark.anyio


async def change(store, user, current: str, new: str = NEW_PASSWORD):
    return await change_password(
        ChangePasswordRequest(current_password=current, new_password=new), user=user, store=store
    )


# --- Camino feliz ---------------------------------------------------------------------------


async def test_chg_f1_saves_new_password_returns_working_token_and_revokes_old_ones(
    auth_store, auth_settings, active_user, clock
):
    old_session = create_access_token(active_user.id, now=clock.ago(seconds=5))
    link, _ = request_reset(auth_store, active_user, auth_settings, clock.now)

    result = await change(auth_store, active_user, PASSWORD)

    assert user_service.authenticate_user(auth_store, active_user.email, NEW_PASSWORD) is not None
    assert user_service.authenticate_user(auth_store, active_user.email, PASSWORD) is None
    # El token nuevo sigue valiendo; el anterior queda revocado.
    assert decode_access_token(result.access_token) == active_user.id
    assert get_current_user(token=result.access_token, store=auth_store).id == active_user.id
    with raises_api_error(401, "session_revoked"):
        get_current_user(token=old_session, store=auth_store)
    # Un enlace de restablecimiento pedido antes ya no sirve.
    assert auth_store.password_resets.get(link.id).used_at is not None


# --- Casos límite ---------------------------------------------------------------------------


async def test_chg_l1_new_password_equal_to_current_is_accepted_and_revokes_sessions(auth_store, active_user, clock):
    old_session = create_access_token(active_user.id, now=clock.ago(seconds=5))

    await change(auth_store, active_user, PASSWORD, PASSWORD)

    assert user_service.authenticate_user(auth_store, active_user.email, PASSWORD) is not None
    with raises_api_error(401, "session_revoked"):
        get_current_user(token=old_session, store=auth_store)


@pytest.mark.parametrize(
    ("current", "new", "field"),
    [("", NEW_PASSWORD, "current_password"), (PASSWORD, "corta12", "new_password")],
    ids=["actual-vacia", "nueva-de-7"],
)
def test_chg_l2_empty_current_or_short_new_password_is_rejected_by_model(current, new, field):
    with pytest.raises(ValidationError) as info:
        ChangePasswordRequest(current_password=current, new_password=new)
    assert [error["loc"] for error in info.value.errors()] == [(field,)]


# --- Modos de fallo -------------------------------------------------------------------------


async def test_chg_x1_wrong_current_password_changes_nothing(auth_store, auth_settings, active_user, clock):
    session = create_access_token(active_user.id, now=clock.ago(seconds=5))
    link, link_token = request_reset(auth_store, active_user, auth_settings, clock.now)

    with raises_api_error(400, "invalid_current_password"):
        await change(auth_store, active_user, "no-es-la-actual")

    stored = auth_store.users.get(active_user.id)
    assert stored.hashed_password == active_user.hashed_password
    assert stored.password_changed_at is None
    assert get_current_user(token=session, store=auth_store).id == active_user.id
    assert auth_store.password_resets.get(link.id).used_at is None
    passwords.check_reset_token(auth_store, link_token, now=clock.now)


async def test_chg_x2_account_deleted_during_change_is_invalid_token_not_wrong_password(auth_store, active_user):
    """Bug H-2 (AUTH-088): la cuenta se borra entre get_current_user y el cambio.

    Antes respondía 400 `invalid_current_password` aunque la contraseña actual fuera correcta.
    Ahora responde lo mismo que get_current_user al token de un usuario borrado.
    """
    authenticated = active_user  # lo que entregó get_current_user
    user_service.delete_user(auth_store, active_user.id)

    with raises_api_error(401, "invalid_token") as info:
        await change(auth_store, authenticated, PASSWORD)

    assert info.value.headers == BEARER_CHALLENGE
    assert auth_store.users.get(active_user.id) is None  # no se recrea la cuenta
