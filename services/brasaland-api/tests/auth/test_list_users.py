"""`GET /users`: la ruta `list_users` y su dependencia `require_admin`."""

import pytest

from app.domains.auth.dependencies import require_admin
from app.domains.users.models import Role
from app.domains.users.router import list_users
from tests.auth.helpers import raises_api_error


def test_lst_f1_admin_lists_every_account_without_password_hash(auth_store, admin_user, active_user, inactive_user):
    users = list_users(_admin=require_admin(admin_user), store=auth_store)

    assert {user.id for user in users} == {admin_user.id, active_user.id, inactive_user.id}
    assert all(not hasattr(user, "hashed_password") for user in users)


def test_lst_l1_only_the_admin_exists(auth_store, admin_user):
    users = list_users(_admin=require_admin(admin_user), store=auth_store)

    assert [user.id for user in users] == [admin_user.id]


@pytest.mark.parametrize("role", [Role.USER, Role.MANAGER])
def test_lst_x1_non_admin_is_forbidden(role, user_factory):
    user = user_factory("equipo@brasaland.com", role=role)

    with raises_api_error(403, "forbidden"):
        require_admin(user)
