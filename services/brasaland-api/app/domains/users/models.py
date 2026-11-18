"""Modelos Pydantic del usuario.

`User` guarda solo credenciales, estado, rol y fecha de alta. El nombre visible y los datos de
contacto viven en `Profile`. El hash de la contraseña nunca sale en una respuesta (`UserPublic`).
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, model_validator

from app.core.security import BCRYPT_MAX_BYTES
from app.domains.profiles.models import Profile, ProfileFields


class Role(StrEnum):
    """Únicos roles válidos según el briefing."""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


VALID_ROLES = [role.value for role in Role]
MIN_PASSWORD_LENGTH = 8


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _check_password(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(
            f"La contraseña no puede superar {BCRYPT_MAX_BYTES} bytes "
            f"(unos {BCRYPT_MAX_BYTES} caracteres sin acentos)."
        )
    return value


# El email se compara sin distinguir mayúsculas: se guarda en minúsculas y sin espacios extremos.
Email = Annotated[EmailStr, BeforeValidator(_strip), AfterValidator(str.lower)]
# La contraseña no se recorta: los espacios forman parte de ella.
Password = Annotated[str, AfterValidator(_check_password)]


class UserCreate(ProfileFields):
    """Entrada de POST /users: credenciales y, opcionalmente, el perfil inicial.

    No acepta `role`: los registros nuevos siempre son `user`. Un admin cambia el rol después.
    """

    model_config = ConfigDict(extra="forbid")

    email: Email = Field(description="Email con el que inicia sesión")
    password: Password = Field(
        description=f"Contraseña de {MIN_PASSWORD_LENGTH} caracteres a {BCRYPT_MAX_BYTES} bytes"
    )


class UserUpdate(BaseModel):
    """Entrada de PUT /users/{id}: solo cambian los campos enviados.

    `role` e `is_active` solo los puede cambiar un admin; lo comprueba el router.
    """

    model_config = ConfigDict(extra="forbid")

    email: Email | None = None
    password: Password | None = None
    role: Role | None = Field(default=None, description="Solo admin: " + ", ".join(VALID_ROLES))
    is_active: bool | None = Field(default=None, description="Solo admin")

    @model_validator(mode="after")
    def check_fields(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("Envía al menos uno de estos campos: email, password, role, is_active.")
        nulls = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(nulls)}.")
        return self


class UserPublic(BaseModel):
    """Lo que la API devuelve de un usuario: nunca incluye el hash de la contraseña."""

    id: str = Field(description="UUID del usuario; otros módulos lo guardan como `user_uuid`")
    email: str
    is_active: bool
    role: Role
    created_at: datetime


class User(UserPublic):
    """Usuario guardado en TinyDB. Solo lo usan el repositorio, los servicios y la autenticación."""

    hashed_password: str
    # Último cambio o restablecimiento de contraseña (AUTH-03), en segundos enteros. Los tokens de
    # acceso emitidos antes dejan de valer. None en las cuentas que nunca la han cambiado.
    password_changed_at: datetime | None = None

    def to_public(self) -> UserPublic:
        return UserPublic(**self.model_dump(exclude={"hashed_password", "password_changed_at"}))


class UserWithProfile(UserPublic):
    """Respuesta de POST /users: el usuario creado y su perfil vinculado."""

    profile: Profile | None
