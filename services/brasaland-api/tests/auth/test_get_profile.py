"""`GET /profiles/{user_id}`: la ruta `read_profile_by_user` (leer: el dueño o un admin)."""

from app.domains.profiles.router import read_profile_by_user
from app.domains.users.models import Role
from tests.auth.helpers import raises_api_error


def test_gpr_f1_owner_reads_own_profile(auth_store, active_user):
    assert read_profile_by_user(active_user.id, current=active_user, store=auth_store).user_id == active_user.id


def test_gpr_f1_admin_reads_another_profile(auth_store, admin_user, active_user):
    assert read_profile_by_user(active_user.id, current=admin_user, store=auth_store).user_id == active_user.id


def test_gpr_l1_manager_is_not_admin_and_cannot_read_another_profile(auth_store, user_factory, active_user):
    manager = user_factory("gerente@brasaland.com", role=Role.MANAGER)

    with raises_api_error(403, "forbidden"):
        read_profile_by_user(active_user.id, current=manager, store=auth_store)


def test_gpr_x1_user_reading_another_profile_is_forbidden(auth_store, active_user, admin_user):
    with raises_api_error(403, "forbidden"):
        read_profile_by_user(admin_user.id, current=active_user, store=auth_store)


def test_gpr_x1_admin_reading_unknown_profile_is_not_found(auth_store, admin_user):
    with raises_api_error(404, "profile_not_found"):
        read_profile_by_user("no-existe", current=admin_user, store=auth_store)
