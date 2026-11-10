"""`POST /users` (registro público): la ruta `register_user`, `service.create_user` y `UserCreate`."""

import pytest
from passlib.hash import bcrypt
from pydantic import ValidationError

from app.domains.users import service as user_service
from app.domains.users.models import Role, UserCreate
from app.domains.users.router import register_user
from tests.auth.helpers import PASSWORD, raises_api_error


def register(store, **fields):
    return register_user(UserCreate(**{"email": "ana@brasaland.com", "password": PASSWORD, **fields}), store=store)


# --- Camino feliz ---------------------------------------------------------------------------


def test_reg_f1_creates_active_user_with_hashed_password_and_profile(auth_store):
    created = register(auth_store, email="  Ana@Brasaland.COM ", name="Ana Gómez", phone="+57 300", address="Calle 1")

    assert (created.email, created.role, created.is_active) == ("ana@brasaland.com", Role.USER, True)
    assert not hasattr(created, "hashed_password")  # la respuesta nunca lleva el hash

    stored = auth_store.users.get(created.id)
    assert stored.hashed_password != PASSWORD
    assert bcrypt.identify(stored.hashed_password)
    assert bcrypt.verify(PASSWORD, stored.hashed_password)

    profile = auth_store.profiles.get_by_user_id(created.id)
    assert profile == created.profile
    assert (profile.name, profile.phone, profile.address) == ("Ana Gómez", "+57 300", "Calle 1")


# --- Casos límite ---------------------------------------------------------------------------


def test_reg_l1_without_profile_data_creates_empty_profile(auth_store):
    created = register(auth_store)

    profile = auth_store.profiles.get_by_user_id(created.id)
    assert profile is not None
    assert (profile.name, profile.phone, profile.address) == (None, None, None)


@pytest.mark.parametrize("password", ["a" * 8, "á" * 36], ids=["8-caracteres", "72-bytes"])
def test_reg_l2_password_at_the_limits_is_accepted(password, auth_store):
    created = register(auth_store, password=password)

    assert user_service.authenticate_user(auth_store, created.email, password) is not None


@pytest.mark.parametrize("password", ["a" * 7, "á" * 36 + "a"], ids=["7-caracteres", "73-bytes"])
def test_reg_l2_password_past_the_limits_is_rejected(password):
    with pytest.raises(ValidationError) as info:
        UserCreate(email="ana@brasaland.com", password=password)
    assert [error["loc"] for error in info.value.errors()] == [("password",)]


@pytest.mark.parametrize("email", ["ANA@brasaland.com", " ana@brasaland.com ", "Ana@Brasaland.Com"])
def test_reg_l3_duplicate_email_in_other_case_or_spaces_is_conflict_and_creates_nothing(email, auth_store, active_user):
    with raises_api_error(409, "duplicate_email"):
        register(auth_store, email=email)

    assert [user.id for user in auth_store.users.list()] == [active_user.id]


# --- Modos de fallo -------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["admin", "user"])
def test_reg_x1_role_field_is_not_accepted(role):
    with pytest.raises(ValidationError) as info:
        UserCreate(email="ana@brasaland.com", password=PASSWORD, role=role)
    assert [(error["loc"], error["type"]) for error in info.value.errors()] == [(("role",), "extra_forbidden")]


@pytest.mark.parametrize("email", ["sin-arroba", "ana@", "@brasaland.com", "ana @brasaland.com", ""])
def test_reg_x2_malformed_email_is_rejected(email):
    with pytest.raises(ValidationError) as info:
        UserCreate(email=email, password=PASSWORD)
    assert [error["loc"] for error in info.value.errors()] == [("email",)]


def test_reg_x3_user_is_not_kept_if_profile_creation_fails(monkeypatch, auth_store):
    def broken(*args, **kwargs):
        raise RuntimeError("fallo simulado al guardar el perfil")

    monkeypatch.setattr(auth_store.profiles, "create_for_user", broken)

    with pytest.raises(RuntimeError):
        register(auth_store)

    assert auth_store.users.list() == []
    assert user_service.get_user_by_email(auth_store, "ana@brasaland.com") is None
