"""`PUT /users/{id}`: la ruta `update_user` (permisos), `service.update_user` y `UserUpdate`."""

import pytest
from pydantic import ValidationError

from app.core.security import create_access_token
from app.domains.auth.dependencies import get_current_user
from app.domains.users import service as user_service
from app.domains.users.models import Role, UserUpdate
from app.domains.users.router import update_user
from tests.auth.helpers import NEW_PASSWORD, PASSWORD, raises_api_error, request_reset


def update(store, user_id, current, **fields):
    return update_user(user_id, UserUpdate(**fields), current=current, store=store)


# --- Camino feliz ---------------------------------------------------------------------------


def test_upd_f1_user_changes_own_email_and_password(auth_store, active_user):
    updated = update(auth_store, active_user.id, active_user, email="Ana.Nueva@Brasaland.com", password=NEW_PASSWORD)

    assert updated.email == "ana.nueva@brasaland.com"
    stored = auth_store.users.get(active_user.id)
    assert stored.hashed_password not in (NEW_PASSWORD, active_user.hashed_password)
    assert user_service.authenticate_user(auth_store, "ana.nueva@brasaland.com", NEW_PASSWORD) is not None
    assert user_service.authenticate_user(auth_store, "ana.nueva@brasaland.com", PASSWORD) is None


def test_upd_f1_admin_changes_role_and_status_of_another_account(auth_store, admin_user, active_user):
    updated = update(auth_store, active_user.id, admin_user, role=Role.MANAGER, is_active=False)

    assert (updated.role, updated.is_active) == (Role.MANAGER, False)
    assert auth_store.users.get(active_user.id).role == Role.MANAGER


# --- Casos límite ---------------------------------------------------------------------------


def test_upd_l1_setting_own_current_email_is_accepted(auth_store, active_user):
    assert update(auth_store, active_user.id, active_user, email=active_user.email.upper()).email == active_user.email


def test_upd_l1_taking_another_accounts_email_in_other_case_is_conflict(auth_store, active_user, admin_user):
    with raises_api_error(409, "duplicate_email"):
        update(auth_store, active_user.id, active_user, email="ADMIN@brasaland.com")

    assert auth_store.users.get(active_user.id).email == active_user.email


@pytest.mark.parametrize(
    "fields",
    [{}, {"email": None}, {"password": None}, {"role": None}, {"is_active": None}],
    ids=["vacio", "email-null", "password-null", "role-null", "is_active-null"],
)
def test_upd_l2_empty_body_or_null_fields_are_rejected_by_model(fields):
    with pytest.raises(ValidationError):
        UserUpdate(**fields)


# --- Modos de fallo -------------------------------------------------------------------------


@pytest.mark.parametrize("role", [Role.USER, Role.MANAGER])
@pytest.mark.parametrize("fields", [{"role": Role.ADMIN}, {"is_active": False}], ids=["role", "is_active"])
def test_upd_x1_non_admin_cannot_change_role_or_status_even_on_own_account(role, fields, auth_store, user_factory):
    user = user_factory("equipo@brasaland.com", role=role)

    with raises_api_error(403, "forbidden"):
        update(auth_store, user.id, user, **fields)

    stored = auth_store.users.get(user.id)
    assert (stored.role, stored.is_active) == (role, True)


def test_upd_x1_non_admin_cannot_sneak_role_alongside_allowed_fields(auth_store, active_user):
    with raises_api_error(403, "forbidden"):
        update(auth_store, active_user.id, active_user, email="otra@brasaland.com", role=Role.ADMIN)

    assert auth_store.users.get(active_user.id).email == active_user.email


def test_upd_x2_user_editing_another_account_is_forbidden(auth_store, active_user, admin_user):
    with raises_api_error(403, "forbidden"):
        update(auth_store, admin_user.id, active_user, email="robada@brasaland.com")

    assert auth_store.users.get(admin_user.id).email == admin_user.email


def test_upd_x2_admin_editing_unknown_id_is_not_found(auth_store, admin_user):
    with raises_api_error(404, "user_not_found"):
        update(auth_store, "no-existe", admin_user, email="nadie@brasaland.com")


def test_upd_x3_password_change_through_this_route_ends_earlier_sessions(auth_store, auth_settings, active_user, clock):
    """Bug H-1 (AUTH-088): cambiar la contraseña por `PUT /users/{id}` debe cerrar las sesiones
    anteriores y anular los enlaces pendientes, como `change-password` y `reset-password`."""
    old_session = create_access_token(active_user.id, now=clock.ago(seconds=5))
    link, _ = request_reset(auth_store, active_user, auth_settings, clock.now)

    update(auth_store, active_user.id, active_user, password=NEW_PASSWORD)

    with raises_api_error(401, "session_revoked"):
        get_current_user(token=old_session, store=auth_store)
    assert auth_store.password_resets.get(link.id).used_at is not None


def test_upd_x3_admin_changing_another_password_ends_that_accounts_sessions(auth_store, admin_user, active_user, clock):
    target_session = create_access_token(active_user.id, now=clock.ago(seconds=5))
    admin_session = create_access_token(admin_user.id, now=clock.ago(seconds=5))

    update(auth_store, active_user.id, admin_user, password=NEW_PASSWORD)

    with raises_api_error(401, "session_revoked"):
        get_current_user(token=target_session, store=auth_store)
    assert get_current_user(token=admin_session, store=auth_store).id == admin_user.id


def test_upd_x3_changes_without_password_keep_sessions_and_links(auth_store, auth_settings, active_user, clock):
    session = create_access_token(active_user.id, now=clock.ago(seconds=5))
    link, _ = request_reset(auth_store, active_user, auth_settings, clock.now)

    update(auth_store, active_user.id, active_user, email="ana.nueva@brasaland.com")

    assert auth_store.users.get(active_user.id).password_changed_at is None
    assert get_current_user(token=session, store=auth_store).id == active_user.id
    assert auth_store.password_resets.get(link.id).used_at is None
