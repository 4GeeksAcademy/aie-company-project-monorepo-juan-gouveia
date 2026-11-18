"""`uv run create-admin`: crea el primer administrador o promueve a un usuario existente.

POST /users es público y siempre crea usuarios con rol `user`, así que el primer admin se crea
desde la consola de quien opera el servidor. La contraseña se pide sin mostrarla en pantalla.
"""

from collections.abc import Callable
from getpass import getpass

from pydantic import TypeAdapter, ValidationError

from app.core.errors import describe_validation_errors
from app.domains.users import service
from app.domains.users.database import AuthStore, get_auth_db_path
from app.domains.users.models import Email, Role, User, UserCreate, UserUpdate

_email_adapter = TypeAdapter(Email)


def promote_to_admin(store: AuthStore, user: User) -> User:
    """Da rol admin al usuario y lo reactiva si estaba desactivado. No toca su contraseña."""
    return service.update_user(store, user.id, UserUpdate(role=Role.ADMIN, is_active=True))


def _messages(error: ValidationError) -> str:
    return " ".join(item["message"] for item in describe_validation_errors(error.errors()))


def main(
    store: AuthStore | None = None,
    read_line: Callable[[str], str] = input,
    read_secret: Callable[[str], str] = getpass,
) -> int:
    """Devuelve el código de salida del proceso: 0 si termina bien, 1 si hay un error de entrada."""
    own_store = store is None
    store = store or AuthStore.from_path(get_auth_db_path())
    try:
        try:
            email = _email_adapter.validate_python(read_line("Email del administrador: "))
        except ValidationError as error:
            print(f"Email no válido. {_messages(error)}")
            return 1

        existing = service.get_user_by_email(store, email)
        if existing is not None:
            if existing.role == Role.ADMIN and existing.is_active:
                print(f"{email} ya es administrador. No se hizo ningún cambio.")
                return 0
            promote_to_admin(store, existing)
            print(f"{email} ya existía: ahora es administrador y está activo. Su contraseña no cambió.")
            return 0

        password = read_secret("Contraseña: ")
        if read_secret("Repite la contraseña: ") != password:
            print("Las contraseñas no coinciden. No se creó el administrador.")
            return 1
        try:
            data = UserCreate(email=email, password=password)
        except ValidationError as error:
            print(f"Contraseña no válida. {_messages(error)}")
            return 1

        service.create_user(store, data, role=Role.ADMIN)
        print(f"Administrador creado: {email}.")
        return 0
    finally:
        if own_store:
            store.close()


def run() -> int:
    """Punto de entrada de `uv run create-admin` (el código devuelto es el de salida del proceso)."""
    print(f"Base de usuarios: {get_auth_db_path()}")
    return main()
