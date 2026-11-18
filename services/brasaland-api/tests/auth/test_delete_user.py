"""`DELETE /users/{id}`: la ruta `delete_user` (permisos) y `service.delete_user`."""

from app.core.security import create_access_token
from app.domains.auth.dependencies import get_current_user
from app.domains.users.router import delete_user
from tests.auth.helpers import raises_api_error, request_reset


def test_del_f1_user_deletes_own_account_with_profile_links_and_session(auth_store, auth_settings, active_user, clock):
    session = create_access_token(active_user.id, now=clock.now)
    link, _ = request_reset(auth_store, active_user, auth_settings, clock.now)

    deleted = delete_user(active_user.id, current=active_user, store=auth_store)

    assert deleted.id == active_user.id
    assert auth_store.users.get(active_user.id) is None
    assert auth_store.profiles.get_by_user_id(active_user.id) is None
    assert auth_store.password_resets.get(link.id) is None
    with raises_api_error(401, "invalid_token"):
        get_current_user(token=session, store=auth_store)


def test_del_l1_admin_deletes_another_account(auth_store, admin_user, active_user):
    delete_user(active_user.id, current=admin_user, store=auth_store)

    assert auth_store.users.get(active_user.id) is None
    assert auth_store.users.get(admin_user.id) is not None


def test_del_x1_user_deleting_another_account_is_forbidden_and_deletes_nothing(auth_store, active_user, admin_user):
    with raises_api_error(403, "forbidden"):
        delete_user(admin_user.id, current=active_user, store=auth_store)

    assert auth_store.users.get(admin_user.id) is not None
    assert auth_store.profiles.get_by_user_id(admin_user.id) is not None


def test_del_x1_admin_deleting_unknown_id_is_not_found(auth_store, admin_user):
    with raises_api_error(404, "user_not_found"):
        delete_user("no-existe", current=admin_user, store=auth_store)
