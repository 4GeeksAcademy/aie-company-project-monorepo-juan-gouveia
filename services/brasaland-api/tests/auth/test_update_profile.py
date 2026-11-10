"""`PUT /profiles/{user_id}`: la ruta `update_profile_by_user` (modificar: solo el dueño, también frente a un admin)."""

from app.domains.profiles.models import ProfileUpdate
from app.domains.profiles.router import update_profile_by_user
from tests.auth.helpers import raises_api_error


def update(store, user_id, current, **fields):
    return update_profile_by_user(user_id, ProfileUpdate(**fields), current=current, store=store)


def test_upr_f1_owner_updates_own_profile_by_id(auth_store, active_user):
    profile = update(auth_store, active_user.id, active_user, name="Ana Gómez")

    assert profile.name == "Ana Gómez"
    assert auth_store.profiles.get_by_user_id(active_user.id).name == "Ana Gómez"


def test_upr_l1_admin_cannot_update_another_profile(auth_store, admin_user, active_user):
    with raises_api_error(403, "forbidden"):
        update(auth_store, active_user.id, admin_user, name="Cambiado por admin")

    assert auth_store.profiles.get_by_user_id(active_user.id).name is None


def test_upr_x1_user_updating_another_profile_is_forbidden_without_changes(auth_store, active_user, admin_user):
    with raises_api_error(403, "forbidden"):
        update(auth_store, admin_user.id, active_user, name="Intruso")

    assert auth_store.profiles.get_by_user_id(admin_user.id).name is None


def test_upr_x1_owner_without_profile_is_not_found(auth_store, active_user):
    auth_store.profiles.delete_for_user(active_user.id)

    with raises_api_error(404, "profile_not_found"):
        update(auth_store, active_user.id, active_user, name="Ana")
