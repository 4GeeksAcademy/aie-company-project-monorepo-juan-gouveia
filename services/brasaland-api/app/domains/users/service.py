"""Capa de servicios de usuarios: las operaciones que piden el briefing y la autenticación.

Reglas que aplica:
- La contraseña se hashea aquí, antes de llegar al repositorio; el texto plano nunca se guarda.
- Crear un usuario crea su perfil en la misma operación, y borrarlo borra también su perfil y sus
  enlaces de restablecimiento de contraseña.
- El email es único (409 en el router).

Los permisos (quién puede cambiar qué) los comprueba el router: estas funciones solo aplican cambios.
"""

import uuid
from datetime import datetime, timezone

from app.core.security import hash_password, verify_password
from app.domains.profiles.models import Profile
from app.domains.users.database import AuthStore
from app.domains.users.exceptions import DuplicateEmailError
from app.domains.users.models import Role, User, UserCreate, UserUpdate


def normalize_email(email: str) -> str:
    """Misma normalización que el modelo: minúsculas y sin espacios extremos."""
    return email.strip().lower()


def create_user(store: AuthStore, data: UserCreate, role: Role = Role.USER) -> tuple[User, Profile]:
    """Registra un usuario con la contraseña hasheada y crea su perfil con los datos opcionales."""
    # El hash es lento a propósito; se calcula fuera del bloqueo para no frenar otras peticiones.
    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        hashed_password=hash_password(data.password),
        is_active=True,
        role=role,
        created_at=datetime.now(timezone.utc),
    )
    with store.lock:
        if store.users.get_by_email(user.email) is not None:
            raise DuplicateEmailError(user.email)
        store.users.insert(user)
        try:
            profile = store.profiles.create_for_user(user.id, data)
        except Exception:
            # Sin perfil no hay usuario: se deshace la inserción.
            store.users.delete(user.id)
            raise
    return user, profile


def get_user_by_id(store: AuthStore, user_id: str) -> User | None:
    return store.users.get(user_id)


def get_user_by_email(store: AuthStore, email: str) -> User | None:
    return store.users.get_by_email(normalize_email(email))


def list_users(store: AuthStore) -> list[User]:
    return store.users.list()


def update_user(store: AuthStore, user_id: str, data: UserUpdate) -> User | None:
    """Aplica los campos enviados. Si llega `password`, se guarda solo su hash. None si no existe."""
    changes = data.model_dump(mode="json", exclude_unset=True)
    if "password" in changes:
        changes["hashed_password"] = hash_password(changes.pop("password"))
    with store.lock:
        if "email" in changes:
            owner = store.users.get_by_email(changes["email"])
            if owner is not None and owner.id != user_id:
                raise DuplicateEmailError(changes["email"])
        return store.users.update(user_id, changes)


def delete_user(store: AuthStore, user_id: str) -> User | None:
    """Elimina el usuario y su perfil vinculado. Devuelve el usuario eliminado, o None si no existía."""
    with store.lock:
        user = store.users.delete(user_id)
        if user is not None:
            store.profiles.delete_for_user(user_id)
            store.password_resets.delete_for_user(user_id)
    return user


def authenticate_user(store: AuthStore, email: str, password: str) -> User | None:
    """Usuario si el email existe y la contraseña coincide con su hash; si no, None.

    Si el email no existe también se ejecuta bcrypt (ver verify_password), para no revelarlo por tiempo.
    El estado `is_active` lo comprueba quien llama, porque responde con otro error.
    """
    user = get_user_by_email(store, email)
    if not verify_password(password, user.hashed_password if user else None):
        return None
    return user
