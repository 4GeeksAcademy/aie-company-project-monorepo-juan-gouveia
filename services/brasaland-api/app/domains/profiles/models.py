"""Modelos Pydantic del perfil.

El nombre visible y los datos de contacto viven aquí y no en `User`, que solo guarda credenciales.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ProfileFields(BaseModel):
    name: Name | None = Field(default=None, description="Nombre visible")
    phone: Phone | None = Field(default=None, description="Teléfono de contacto")
    address: Address | None = Field(default=None, description="Dirección de contacto")


class ProfileUpdate(ProfileFields):
    """Entrada de PUT /profiles/me: solo cambian los campos enviados; `null` vacía el campo."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("Envía al menos uno de estos campos: name, phone, address.")
        return self


class ProfileRead(BaseModel):
    """Salida de las rutas de perfil y del perfil anidado en GET /auth/me: solo nombre y contacto.

    No incluye `id` ni `user_id`: el primero es interno (ninguna ruta lo acepta) y el segundo ya lo
    conoce quien llama (es él mismo o el `user_id` de la URL). Ver docs/serialization-audit.md (4.3).
    """

    name: str | None = Field(description="Nombre visible")
    phone: str | None = Field(description="Teléfono de contacto")
    address: str | None = Field(description="Dirección de contacto")


class Profile(ProfileFields):
    """Perfil guardado, vinculado uno a uno con su usuario mediante `user_id`. No sale de la API tal cual."""

    id: str = Field(description="UUID del perfil")
    user_id: str = Field(description="UUID del usuario dueño del perfil")

    def to_read(self) -> ProfileRead:
        return ProfileRead(name=self.name, phone=self.phone, address=self.address)
