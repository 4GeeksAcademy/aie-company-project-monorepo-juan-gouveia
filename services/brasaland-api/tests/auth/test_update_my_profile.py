"""`PUT /profiles/me`: la ruta `update_my_profile` y las reglas de `ProfileUpdate`."""

import pytest
from pydantic import ValidationError

from app.domains.profiles.models import ProfileUpdate
from app.domains.profiles.router import update_my_profile
from tests.auth.helpers import raises_api_error

LIMITS = {"name": 120, "phone": 30, "address": 200}


@pytest.fixture
def ana(user_factory):
    return user_factory("ana@brasaland.com", name="Ana Gómez", phone="+57 300", address="Calle 1")


def update(store, user, **fields):
    return update_my_profile(ProfileUpdate(**fields), user=user, store=store)


def test_upm_f1_sending_only_phone_changes_only_phone(auth_store, ana):
    profile = update(auth_store, ana, phone="+57 311")

    assert (profile.name, profile.phone, profile.address) == ("Ana Gómez", "+57 311", "Calle 1")
    assert auth_store.profiles.get_by_user_id(ana.id) == profile


def test_upm_l1_null_empties_the_field(auth_store, ana):
    profile = update(auth_store, ana, address=None)

    assert (profile.name, profile.address) == ("Ana Gómez", None)


def test_upm_l1_surrounding_spaces_are_trimmed(auth_store, ana):
    assert update(auth_store, ana, name="  Ana María  ").name == "Ana María"


@pytest.mark.parametrize("field", LIMITS)
def test_upm_l1_maximum_length_is_accepted_and_one_more_rejected(field, auth_store, ana):
    limit = LIMITS[field]

    assert getattr(update(auth_store, ana, **{field: "x" * limit}), field) == "x" * limit
    with pytest.raises(ValidationError) as info:
        ProfileUpdate(**{field: "x" * (limit + 1)})
    assert [error["loc"] for error in info.value.errors()] == [(field,)]


@pytest.mark.parametrize(
    "fields",
    [{}, {"email": "otra@brasaland.com"}, {"name": "   "}],
    ids=["vacio", "campo-desconocido", "nombre-solo-espacios"],
)
def test_upm_x1_invalid_body_is_rejected_by_model(fields):
    with pytest.raises(ValidationError):
        ProfileUpdate(**fields)


def test_upm_x2_user_without_profile_is_not_found(auth_store, active_user):
    auth_store.profiles.delete_for_user(active_user.id)

    with raises_api_error(404, "profile_not_found"):
        update(auth_store, active_user, phone="+57 300")
