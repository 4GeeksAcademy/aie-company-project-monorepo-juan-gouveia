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


class Profile(ProfileFields):
    """Perfil guardado, vinculado uno a uno con su usuario mediante `user_id`."""

    id: str = Field(description="UUID del perfil")
    user_id: str = Field(description="UUID del usuario dueño del perfil")
