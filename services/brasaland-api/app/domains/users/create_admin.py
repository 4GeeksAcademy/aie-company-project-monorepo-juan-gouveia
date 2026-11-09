"""`uv run create-admin`: crea el primer administrador o promueve a un usuario existente.

POST /users es público y siempre crea usuarios con rol `user`, así que el primer admin se crea
desde la consola de quien opera el servidor. La contraseña se pide sin mostrarla en pantalla.
"""

import json
import sys
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


def _error(message: str) -> None:
    """Los errores van a stderr; stdout queda para el resultado."""
    print(message, file=sys.stderr)


def main(
    store: AuthStore | None = None,
    read_line: Callable[[str], str] = input,
    read_secret: Callable[[str], str] = getpass,
) -> int:
    """Devuelve el código de salida del proceso: 0 si termina bien, 1 si hay un error y 130 si se
    cancela con Ctrl+C (el código habitual de una interrupción).

    Todas las preguntas se hacen antes de escribir en la base, así que cancelar no deja cambios.
    """
    own_store = store is None
    if store is None:
        try:
            store = AuthStore.from_path(get_auth_db_path())
        except OSError as error:
            _error(f"No se puede abrir la base de usuarios: {error.strerror or error}.")
            return 1
    try:
        return _create_or_promote(store, read_line, read_secret)
    except KeyboardInterrupt:
        _error("\nCancelado. No se hizo ningún cambio.")
        return 130
    except EOFError:
        # Sin entrada disponible (por ejemplo, con stdin cerrado o redirigido desde un archivo vacío).
        _error("\nNo hay entrada para responder. No se hizo ningún cambio.")
        return 1
    except json.JSONDecodeError:
        # TinyDB lee el archivo en la primera consulta, antes de escribir nada.
        _error("La base de usuarios no es un JSON válido y no se ha modificado. Revisa el archivo o restáuralo.")
        return 1
    except OSError as error:
        _error(f"No se pudo leer o escribir la base de usuarios: {error.strerror or error}.")
        return 1
    finally:
        if own_store:
            store.close()


def _create_or_promote(
    store: AuthStore,
    read_line: Callable[[str], str],
    read_secret: Callable[[str], str],
) -> int:
    try:
        email = _email_adapter.validate_python(read_line("Email del administrador: "))
    except ValidationError as error:
        _error(f"Email no válido. {_messages(error)}")
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
        _error("Las contraseñas no coinciden. No se creó el administrador.")
        return 1
    try:
        data = UserCreate(email=email, password=password)
    except ValidationError as error:
        _error(f"Contraseña no válida. {_messages(error)}")
        return 1

    service.create_user(store, data, role=Role.ADMIN)
    print(f"Administrador creado: {email}.")
    return 0


def run() -> int:
    """Punto de entrada de `uv run create-admin` (el código devuelto es el de salida del proceso)."""
    # Ruta absoluta a propósito: solo la ve quien opera el servidor y le confirma qué archivo se usa
    # (AUTH_DB_PATH puede apuntar a cualquier sitio). La API nunca la devuelve a un cliente.
    print(f"Base de usuarios: {get_auth_db_path()}")
    return main()
