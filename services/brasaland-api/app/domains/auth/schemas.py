"""Entradas y respuestas de los endpoints de autenticación."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domains.profiles.models import Profile
from app.domains.users.models import Role


class LoginRequest(BaseModel):
    """Credenciales del login. El email no se valida como formato: si no existe, la respuesta es la
    misma que con una contraseña incorrecta (401), para no revelar qué emails están registrados."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, description="Email con el que se registró el usuario")
    password: str = Field(min_length=1, description="Contraseña")


class Token(BaseModel):
    access_token: str = Field(description="JWT firmado; envíalo en la cabecera Authorization: Bearer <token>")
    token_type: Literal["bearer"] = "bearer"


class CurrentUser(BaseModel):
    """Respuesta de GET /auth/me: credenciales visibles del usuario y su perfil."""

    id: str = Field(description="UUID del usuario (`user_uuid` en otros módulos)")
    email: str
    role: Role
    profile: Profile | None = Field(description="Nombre visible y datos de contacto")
