"""`GET /users/{id}`: la ruta `get_user` (permiso `ensure_self_or_admin` y búsqueda)."""

import pytest

from app.domains.users.router import get_user
from tests.auth.helpers import raises_api_error


def test_get_f1_user_reads_own_account_without_hash(auth_store, active_user):
    found = get_user(active_user.id, current=active_user, store=auth_store)

    assert (found.id, found.email) == (active_user.id, active_user.email)
    assert not hasattr(found, "hashed_password")


def test_get_f1_admin_reads_another_account(auth_store, admin_user, active_user):
    assert get_user(active_user.id, current=admin_user, store=auth_store).id == active_user.id


def test_get_l1_admin_asking_for_unknown_id_is_not_found(auth_store, admin_user):
    with raises_api_error(404, "user_not_found"):
        get_user("no-existe", current=admin_user, store=auth_store)


@pytest.mark.parametrize("target", ["existing", "missing"])
def test_get_x1_user_asking_for_other_account_is_forbidden_whether_or_not_it_exists(
    target, auth_store, active_user, admin_user
):
    user_id = admin_user.id if target == "existing" else "no-existe"

    # El 403 llega antes de buscar: la respuesta no revela si el ID existe.
    with raises_api_error(403, "forbidden"):
        get_user(user_id, current=active_user, store=auth_store)
