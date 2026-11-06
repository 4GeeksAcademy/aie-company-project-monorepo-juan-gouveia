"""Entradas y respuestas de los endpoints de autenticación."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domains.profiles.models import Profile
from app.domains.users.models import Email, Password, Role


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


# --- Restablecimiento y cambio de contraseña (AUTH-03) ----------------------------------------

FORGOT_PASSWORD_MESSAGE = "Si esa dirección está registrada, recibirás un enlace en breve."


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email = Field(description="Email de la cuenta")


class ResetTokenCheck(BaseModel):
    """Entrada de POST /auth/reset-password/validate: el token va en el cuerpo, no en la URL,
    para que no quede en los logs de acceso."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, description="Token del enlace de restablecimiento")


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, description="Token del enlace de restablecimiento (parámetro `token` de la URL)")
    new_password: Password = Field(description="Contraseña nueva, con las mismas reglas que en el registro")


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, description="Contraseña actual")
    new_password: Password = Field(description="Contraseña nueva, con las mismas reglas que en el registro")


class MessageResponse(BaseModel):
    message: str


class PasswordChanged(Token):
    """Respuesta de POST /auth/change-password: los tokens anteriores dejan de valer; este los sustituye."""

    message: str = "Contraseña actualizada."
