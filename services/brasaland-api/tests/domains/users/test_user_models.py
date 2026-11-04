"""Validación de entradas de usuario: roles del briefing, email normalizado y contraseña."""

import pytest
from pydantic import ValidationError

from app.core.errors import describe_validation_errors
from app.domains.users.models import VALID_ROLES, Role, User, UserCreate, UserUpdate


def fields(error: ValidationError) -> set[str]:
    return {item["field"] for item in describe_validation_errors(error.errors())}


def test_roles_are_exactly_the_briefing_ones():
    assert VALID_ROLES == ["admin", "manager", "user"]


def test_create_accepts_credentials_and_optional_profile():
    data = UserCreate(email="Ana@Brasaland.com ", password="parrilla-segura", name="Ana", phone="+57 300", address="Medellín")
    assert data.email == "ana@brasaland.com"
    assert (data.name, data.phone, data.address) == ("Ana", "+57 300", "Medellín")


def test_create_profile_fields_are_optional():
    data = UserCreate(email="ana@brasaland.com", password="parrilla-segura")
    assert data.name is None and data.phone is None and data.address is None


@pytest.mark.parametrize("role", ["admin", "user", "superadmin"])
def test_create_does_not_accept_role(role):
    # Los registros nuevos siempre son `user`: el campo `role` no se admite en el alta.
    with pytest.raises(ValidationError) as error:
        UserCreate(email="ana@brasaland.com", password="parrilla-segura", role=role)
    assert fields(error.value) == {"role"}


@pytest.mark.parametrize("field", ["id", "hashed_password", "is_active", "created_at"])
def test_create_rejects_system_fields(field):
    with pytest.raises(ValidationError) as error:
        UserCreate(email="ana@brasaland.com", password="parrilla-segura", **{field: "x"})
    assert fields(error.value) == {field}


@pytest.mark.parametrize("email", ["", "ana", "ana@", "@brasaland.com"])
def test_invalid_email_is_rejected_with_spanish_message(email):
    with pytest.raises(ValidationError) as error:
        UserCreate(email=email, password="parrilla-segura")
    details = describe_validation_errors(error.value.errors())
    assert details == [{"field": "email", "message": "No es un email válido."}]


def test_short_password_is_rejected():
    with pytest.raises(ValidationError) as error:
        UserCreate(email="ana@brasaland.com", password="corta")
    assert describe_validation_errors(error.value.errors())[0]["message"] == (
        "La contraseña debe tener al menos 8 caracteres."
    )


def test_password_over_72_bytes_is_rejected():
    # 37 caracteres "ñ" ocupan 74 bytes: bcrypt no los admitiría.
    with pytest.raises(ValidationError) as error:
        UserCreate(email="ana@brasaland.com", password="ñ" * 37)
    assert fields(error.value) == {"password"}


def test_password_of_72_bytes_is_accepted_and_not_stripped():
    assert UserCreate(email="ana@brasaland.com", password=" " + "a" * 71).password == " " + "a" * 71


def test_update_accepts_known_roles_and_rejects_others():
    assert UserUpdate(role="manager").role == Role.MANAGER
    with pytest.raises(ValidationError) as error:
        UserUpdate(role="superadmin")
    assert describe_validation_errors(error.value.errors()) == [
        {"field": "role", "message": "Debe ser uno de estos valores: 'admin', 'manager' o 'user'."}
    ]


def test_update_needs_at_least_one_field():
    with pytest.raises(ValidationError, match="al menos uno"):
        UserUpdate()


def test_update_rejects_explicit_null():
    with pytest.raises(ValidationError, match="no pueden ser null: email"):
        UserUpdate(email=None)


def test_update_rejects_unknown_and_profile_fields():
    # El nombre se cambia en /profiles/me, no en el usuario.
    with pytest.raises(ValidationError) as error:
        UserUpdate(name="Ana")
    assert fields(error.value) == {"name"}


def test_public_user_has_no_password_hash():
    user = User(
        id="u-1",
        email="ana@brasaland.com",
        hashed_password="$2b$12$hash",
        is_active=True,
        role="user",
        created_at="2026-11-04T12:00:00+00:00",
    )
    public = user.to_public().model_dump()
    assert "hashed_password" not in public
    assert set(public) == {"id", "email", "is_active", "role", "created_at"}
