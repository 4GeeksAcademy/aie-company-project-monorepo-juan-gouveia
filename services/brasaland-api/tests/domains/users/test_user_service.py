"""Capa de servicios y almacenamiento TinyDB de usuarios y perfiles."""

import json
import uuid

import pytest

from app.domains.users import service
from app.domains.users.database import AuthStore, get_auth_db_path
from app.domains.users.exceptions import DuplicateEmailError
from app.domains.users.models import Role, UserCreate, UserUpdate

PASSWORD = "parrilla-segura"


def new_user(email="ana@brasaland.com", **profile) -> UserCreate:
    return UserCreate(email=email, password=PASSWORD, **profile)


def stored_json(store: AuthStore, tmp_path) -> dict:
    return json.loads((tmp_path / "auth-test.json").read_text(encoding="utf-8"))


# --- Crear -------------------------------------------------------------------------------


def test_create_user_defaults_and_uuid(auth_store):
    user, _ = service.create_user(auth_store, new_user())
    assert uuid.UUID(user.id).version == 4
    assert user.role == Role.USER
    assert user.is_active is True
    assert user.created_at.tzinfo is not None


def test_create_user_creates_linked_profile_with_contact_data(auth_store):
    user, profile = service.create_user(auth_store, new_user(name="Ana", phone="+57 300", address="Medellín"))
    assert profile.user_id == user.id
    assert (profile.name, profile.phone, profile.address) == ("Ana", "+57 300", "Medellín")
    assert auth_store.profiles.get_by_user_id(user.id) == profile


def test_create_user_without_profile_data_still_creates_empty_profile(auth_store):
    user, profile = service.create_user(auth_store, new_user())
    assert profile.user_id == user.id
    assert profile.name is None and profile.phone is None and profile.address is None


def test_name_and_contact_are_stored_in_profile_not_in_user(auth_store, tmp_path):
    service.create_user(auth_store, new_user(name="Ana", phone="+57 300", address="Medellín"))
    data = stored_json(auth_store, tmp_path)
    (user_document,) = data["users"].values()
    (profile_document,) = data["profiles"].values()
    assert set(user_document) == {"id", "email", "hashed_password", "is_active", "role", "created_at"}
    assert {"name", "phone", "address"} <= set(profile_document)


def test_plain_password_never_reaches_the_database(auth_store, tmp_path):
    service.create_user(auth_store, new_user())
    service.update_user(auth_store, service.get_user_by_email(auth_store, "ana@brasaland.com").id,
                        UserUpdate(password="nueva-clave-segura"))
    raw = (tmp_path / "auth-test.json").read_text(encoding="utf-8")
    assert PASSWORD not in raw and "nueva-clave-segura" not in raw
    assert "$2b$" in raw


def test_duplicate_email_is_rejected_case_insensitive(auth_store):
    service.create_user(auth_store, new_user())
    with pytest.raises(DuplicateEmailError):
        service.create_user(auth_store, new_user(email="ANA@brasaland.com"))
    assert len(service.list_users(auth_store)) == 1


def test_create_with_role_for_admin_script(auth_store):
    user, _ = service.create_user(auth_store, new_user(), role=Role.ADMIN)
    assert user.role == Role.ADMIN


# --- Leer --------------------------------------------------------------------------------


def test_get_by_id_and_by_email(auth_store):
    user, _ = service.create_user(auth_store, new_user())
    assert service.get_user_by_id(auth_store, user.id) == user
    assert service.get_user_by_email(auth_store, "  Ana@Brasaland.COM ") == user
    assert service.get_user_by_id(auth_store, "no-existe") is None
    assert service.get_user_by_email(auth_store, "otra@brasaland.com") is None


def test_list_users_by_creation_date(auth_store):
    first, _ = service.create_user(auth_store, new_user("a@brasaland.com"))
    second, _ = service.create_user(auth_store, new_user("b@brasaland.com"))
    assert [user.id for user in service.list_users(auth_store)] == [first.id, second.id]


# --- Actualizar --------------------------------------------------------------------------


def test_update_changes_only_sent_fields(auth_store):
    user, _ = service.create_user(auth_store, new_user())
    updated = service.update_user(auth_store, user.id, UserUpdate(role="manager"))
    assert updated.role == Role.MANAGER
    assert updated.email == user.email
    assert updated.hashed_password == user.hashed_password
    assert updated.created_at == user.created_at


def test_update_password_stores_new_hash(auth_store):
    user, _ = service.create_user(auth_store, new_user())
    service.update_user(auth_store, user.id, UserUpdate(password="nueva-clave-segura"))
    assert service.authenticate_user(auth_store, user.email, "nueva-clave-segura") is not None
    assert service.authenticate_user(auth_store, user.email, PASSWORD) is None


def test_update_email_to_one_in_use_is_rejected(auth_store):
    service.create_user(auth_store, new_user("a@brasaland.com"))
    other, _ = service.create_user(auth_store, new_user("b@brasaland.com"))
    with pytest.raises(DuplicateEmailError):
        service.update_user(auth_store, other.id, UserUpdate(email="A@brasaland.com"))


def test_update_email_to_own_email_is_allowed(auth_store):
    user, _ = service.create_user(auth_store, new_user())
    assert service.update_user(auth_store, user.id, UserUpdate(email="ana@brasaland.com")).email == user.email


def test_update_missing_user_returns_none(auth_store):
    assert service.update_user(auth_store, "no-existe", UserUpdate(is_active=False)) is None


# --- Eliminar ----------------------------------------------------------------------------


def test_delete_removes_user_and_linked_profile(auth_store):
    user, _ = service.create_user(auth_store, new_user(name="Ana"))
    other, other_profile = service.create_user(auth_store, new_user("b@brasaland.com", name="Bea"))
    assert service.delete_user(auth_store, user.id) == user
    assert service.get_user_by_id(auth_store, user.id) is None
    assert auth_store.profiles.get_by_user_id(user.id) is None
    # El otro usuario y su perfil siguen intactos.
    assert auth_store.profiles.get_by_user_id(other.id) == other_profile


def test_delete_missing_user_returns_none(auth_store):
    assert service.delete_user(auth_store, "no-existe") is None


# --- Autenticar --------------------------------------------------------------------------


def test_authenticate_with_right_and_wrong_credentials(auth_store):
    user, _ = service.create_user(auth_store, new_user())
    assert service.authenticate_user(auth_store, "ANA@brasaland.com", PASSWORD) == user
    assert service.authenticate_user(auth_store, "ana@brasaland.com", "otra-clave-cualquiera") is None
    assert service.authenticate_user(auth_store, "nadie@brasaland.com", PASSWORD) is None


# --- Persistencia ------------------------------------------------------------------------


def test_data_persists_in_file_between_instances(tmp_path):
    path = tmp_path / "persist.json"
    first = AuthStore.from_path(path)
    user, profile = service.create_user(first, new_user(name="Ana"))
    first.close()

    second = AuthStore.from_path(path)
    try:
        assert service.get_user_by_id(second, user.id) == user
        assert second.profiles.get_by_user_id(user.id) == profile
    finally:
        second.close()


def test_db_path_is_configurable(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "otra.json"))
    assert get_auth_db_path() == (tmp_path / "otra.json").resolve()
    monkeypatch.delenv("AUTH_DB_PATH")
    assert get_auth_db_path().parts[-2:] == ("storage", "auth-db.json")
