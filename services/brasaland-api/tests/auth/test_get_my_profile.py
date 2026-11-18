"""`GET /profiles/me`: la ruta `read_my_profile`."""

from app.domains.profiles.router import read_my_profile
from tests.auth.helpers import raises_api_error


def test_pme_f1_returns_own_profile(auth_store, user_factory):
    user = user_factory("ana@brasaland.com", name="Ana Gómez", address="Calle 1")

    profile = read_my_profile(user=user, store=auth_store)

    # Solo nombre y contacto: sin `id` ni `user_id` (docs/serialization-audit.md, P1).
    assert profile.model_dump() == {"name": "Ana Gómez", "phone": None, "address": "Calle 1"}


def test_pme_l1_profile_with_all_fields_empty(auth_store, active_user):
    profile = read_my_profile(user=active_user, store=auth_store)

    assert profile.model_dump() == {"name": None, "phone": None, "address": None}


def test_pme_x1_user_without_profile_is_not_found(auth_store, active_user):
    auth_store.profiles.delete_for_user(active_user.id)

    with raises_api_error(404, "profile_not_found"):
        read_my_profile(user=active_user, store=auth_store)
