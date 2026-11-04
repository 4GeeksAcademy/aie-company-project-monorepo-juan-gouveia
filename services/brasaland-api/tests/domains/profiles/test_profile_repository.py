"""Modelo y repositorio de perfiles (vínculo uno a uno con el usuario)."""

import uuid

import pytest
from pydantic import ValidationError

from app.domains.profiles.models import ProfileFields, ProfileUpdate

USER_ID = "3f1c2a4e-8b7d-4c6e-9a0b-1d2e3f4a5b6c"


def test_create_for_user_assigns_uuid_and_link(auth_store):
    profile = auth_store.profiles.create_for_user(USER_ID, ProfileFields(name=" Ana ", phone="+57 300"))
    assert uuid.UUID(profile.id).version == 4
    assert profile.user_id == USER_ID
    assert (profile.name, profile.phone, profile.address) == ("Ana", "+57 300", None)


def test_update_changes_only_sent_fields_and_null_clears(auth_store):
    auth_store.profiles.create_for_user(USER_ID, ProfileFields(name="Ana", phone="+57 300", address="Medellín"))
    updated = auth_store.profiles.update_for_user(USER_ID, ProfileUpdate(name="Ana María", phone=None))
    assert (updated.name, updated.phone, updated.address) == ("Ana María", None, "Medellín")
    assert auth_store.profiles.get_by_user_id(USER_ID) == updated


def test_update_and_delete_without_profile(auth_store):
    assert auth_store.profiles.update_for_user(USER_ID, ProfileUpdate(name="Ana")) is None
    assert auth_store.profiles.delete_for_user(USER_ID) is False


def test_update_needs_at_least_one_field():
    with pytest.raises(ValidationError, match="al menos uno"):
        ProfileUpdate()


@pytest.mark.parametrize("payload", [{"user_id": "otro"}, {"id": "x"}, {"email": "a@b.co"}])
def test_update_rejects_link_and_unknown_fields(payload):
    # Nadie puede reasignar su perfil a otro usuario.
    with pytest.raises(ValidationError):
        ProfileUpdate(**payload)


@pytest.mark.parametrize("payload", [{"name": "   "}, {"phone": "1" * 31}, {"address": "x" * 201}])
def test_update_rejects_empty_or_too_long_values(payload):
    with pytest.raises(ValidationError):
        ProfileUpdate(**payload)
