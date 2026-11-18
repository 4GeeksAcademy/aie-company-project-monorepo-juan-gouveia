"""`uv run create-admin`: crear el primer admin o promover a un usuario existente."""

import pytest

from app.domains.users import create_admin, service
from app.domains.users.create_admin import main
from app.domains.users.models import Role, UserCreate, UserUpdate


def answers(*values):
    """Simula lo que escribe la persona en la consola, en orden."""
    queue = list(values)
    return lambda _prompt: queue.pop(0)


def test_creates_admin_with_hashed_password(auth_store, capsys):
    code = main(auth_store, read_line=answers("Admin@Brasaland.com"), read_secret=answers("clave-admin-1", "clave-admin-1"))
    assert code == 0
    admin = service.get_user_by_email(auth_store, "admin@brasaland.com")
    assert admin.role == Role.ADMIN and admin.is_active
    assert admin.hashed_password != "clave-admin-1"
    assert service.authenticate_user(auth_store, "admin@brasaland.com", "clave-admin-1") == admin
    assert auth_store.profiles.get_by_user_id(admin.id) is not None
    assert "Administrador creado" in capsys.readouterr().out


def test_promotes_existing_user_and_keeps_password(auth_store, capsys):
    user, _ = service.create_user(auth_store, UserCreate(email="ana@brasaland.com", password="clave-de-ana"))
    service.update_user(auth_store, user.id, UserUpdate(is_active=False))

    code = main(auth_store, read_line=answers("ana@brasaland.com"), read_secret=answers())
    assert code == 0
    promoted = service.get_user_by_id(auth_store, user.id)
    assert promoted.role == Role.ADMIN and promoted.is_active
    assert service.authenticate_user(auth_store, "ana@brasaland.com", "clave-de-ana") is not None
    assert "ahora es administrador" in capsys.readouterr().out


def test_existing_admin_is_left_unchanged(auth_store, capsys):
    service.create_user(auth_store, UserCreate(email="admin@brasaland.com", password="clave-admin-1"), role=Role.ADMIN)
    assert main(auth_store, read_line=answers("admin@brasaland.com"), read_secret=answers()) == 0
    assert "ya es administrador" in capsys.readouterr().out


def test_invalid_email_fails(auth_store, capsys):
    assert main(auth_store, read_line=answers("no-es-email"), read_secret=answers()) == 1
    assert "Email no válido" in capsys.readouterr().err
    assert service.list_users(auth_store) == []


def test_mismatched_passwords_fail(auth_store, capsys):
    code = main(auth_store, read_line=answers("admin@brasaland.com"), read_secret=answers("clave-admin-1", "clave-admin-2"))
    assert code == 1
    assert "no coinciden" in capsys.readouterr().err
    assert service.list_users(auth_store) == []


def test_short_password_fails(auth_store, capsys):
    code = main(auth_store, read_line=answers("admin@brasaland.com"), read_secret=answers("corta", "corta"))
    assert code == 1
    assert "al menos 8 caracteres" in capsys.readouterr().err
    assert service.list_users(auth_store) == []


def raises(error):
    def read(_prompt):
        raise error
    return read


@pytest.mark.parametrize(
    ("error", "code", "message"),
    [(KeyboardInterrupt(), 130, "Cancelado"), (EOFError(), 1, "No hay entrada")],
)
def test_cancelled_input_changes_nothing(auth_store, capsys, error, code, message):
    assert main(auth_store, read_line=raises(error), read_secret=answers()) == code
    err = capsys.readouterr().err
    assert message in err and "No se hizo ningún cambio" in err
    assert service.list_users(auth_store) == []


def test_ctrl_c_at_password_prompt_changes_nothing(auth_store, capsys):
    code = main(auth_store, read_line=answers("admin@brasaland.com"), read_secret=raises(KeyboardInterrupt()))
    assert code == 130
    assert service.list_users(auth_store) == []


def test_corrupt_database_is_reported_and_left_untouched(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "auth.json"
    db_path.write_text("{corrupto", encoding="utf-8")
    monkeypatch.setattr(create_admin, "get_auth_db_path", lambda: db_path)
    assert main(read_line=answers("admin@brasaland.com"), read_secret=answers()) == 1
    assert "no es un JSON válido" in capsys.readouterr().err
    assert db_path.read_text(encoding="utf-8") == "{corrupto"


def test_database_that_cannot_be_opened_is_reported(monkeypatch, capsys):
    def denied(_path):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(create_admin.AuthStore, "from_path", staticmethod(denied))
    assert main(read_line=answers(), read_secret=answers()) == 1
    assert "No se puede abrir la base de usuarios: Permission denied." in capsys.readouterr().err
