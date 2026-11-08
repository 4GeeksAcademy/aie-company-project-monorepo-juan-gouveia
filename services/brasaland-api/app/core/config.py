"""Configuración que la API lee del entorno.

Los valores sensibles (la clave de firma de los JWT) y la validez del token no tienen valor por
defecto en el código: si faltan o no son válidos, la API no arranca y dice qué variable revisar.
En local se cargan desde `.env` con `uv run --env-file .env ...` (ver `.env.example`).

Restablecimiento de contraseña y correo (ticket AUTH-03):
- PASSWORD_RESET_EXPIRE_MINUTES: validez del enlace, 30 por defecto y entre 15 y 60.
- RESEND_API_KEY: opcional. Sin ella la API arranca, pero no envía correos (lo avisa en el log).
- EMAIL_FROM: remitente; por defecto, el de pruebas de Resend.
- FRONTEND_URL: dirección del backoffice, para construir el enlace de restablecimiento.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache

# Prefijo común de las rutas de la API (propuesta de arquitectura, 3.3).
API_PREFIX = "/api/v1"

SECRET_KEY_ENV = "SECRET_KEY"
ACCESS_TOKEN_EXPIRE_MINUTES_ENV = "ACCESS_TOKEN_EXPIRE_MINUTES"
MIN_SECRET_KEY_LENGTH = 32

PASSWORD_RESET_EXPIRE_MINUTES_ENV = "PASSWORD_RESET_EXPIRE_MINUTES"
DEFAULT_PASSWORD_RESET_EXPIRE_MINUTES = 30
# Ventana que pide el ticket AUTH-03 para el enlace de restablecimiento.
MIN_PASSWORD_RESET_MINUTES = 15
MAX_PASSWORD_RESET_MINUTES = 60

RESEND_API_KEY_ENV = "RESEND_API_KEY"
EMAIL_FROM_ENV = "EMAIL_FROM"
# Remitente de pruebas de Resend: sin dominio verificado solo entrega al email de la cuenta de Resend.
DEFAULT_EMAIL_FROM = "Brasaland <onboarding@resend.dev>"
FRONTEND_URL_ENV = "FRONTEND_URL"
DEFAULT_FRONTEND_URL = "http://localhost:3001"


class ConfigError(RuntimeError):
    """Falta una variable de entorno obligatoria o su valor no es válido."""


@dataclass(frozen=True)
class Settings:
    # repr=False: la clave nunca aparece al imprimir la configuración ni en un traceback.
    secret_key: str = field(repr=False)
    access_token_expire_minutes: int
    password_reset_expire_minutes: int = DEFAULT_PASSWORD_RESET_EXPIRE_MINUTES
    # None: el envío de correos está desactivado. repr=False por el mismo motivo que la clave.
    resend_api_key: str | None = field(default=None, repr=False)
    email_from: str = DEFAULT_EMAIL_FROM
    # Sin barra final: el enlace se construye como f"{frontend_url}/reset-password?token=...".
    frontend_url: str = DEFAULT_FRONTEND_URL

    @property
    def email_enabled(self) -> bool:
        return self.resend_api_key is not None


def load_settings(environ: Mapping[str, str] = os.environ) -> Settings:
    """Lee y valida la configuración; lanza ConfigError con un mensaje que nombra la variable."""
    secret_key = environ.get(SECRET_KEY_ENV, "").strip()
    if not secret_key:
        raise ConfigError(f"Falta la variable de entorno {SECRET_KEY_ENV} (clave de firma de los JWT).")
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise ConfigError(f"{SECRET_KEY_ENV} debe tener al menos {MIN_SECRET_KEY_LENGTH} caracteres.")

    raw_minutes = environ.get(ACCESS_TOKEN_EXPIRE_MINUTES_ENV, "").strip()
    if not raw_minutes:
        raise ConfigError(
            f"Falta la variable de entorno {ACCESS_TOKEN_EXPIRE_MINUTES_ENV} (minutos de validez del token)."
        )
    try:
        minutes = int(raw_minutes)
    except ValueError:
        minutes = 0
    if minutes <= 0:
        raise ConfigError(f"{ACCESS_TOKEN_EXPIRE_MINUTES_ENV} debe ser un número entero mayor que 0.")

    return Settings(
        secret_key=secret_key,
        access_token_expire_minutes=minutes,
        password_reset_expire_minutes=_load_reset_minutes(environ),
        resend_api_key=environ.get(RESEND_API_KEY_ENV, "").strip() or None,
        email_from=environ.get(EMAIL_FROM_ENV, "").strip() or DEFAULT_EMAIL_FROM,
        frontend_url=_load_frontend_url(environ),
    )


def _load_reset_minutes(environ: Mapping[str, str]) -> int:
    raw = environ.get(PASSWORD_RESET_EXPIRE_MINUTES_ENV, "").strip()
    if not raw:
        return DEFAULT_PASSWORD_RESET_EXPIRE_MINUTES
    try:
        minutes = int(raw)
    except ValueError:
        minutes = 0
    if not MIN_PASSWORD_RESET_MINUTES <= minutes <= MAX_PASSWORD_RESET_MINUTES:
        raise ConfigError(
            f"{PASSWORD_RESET_EXPIRE_MINUTES_ENV} debe ser un número entero entre "
            f"{MIN_PASSWORD_RESET_MINUTES} y {MAX_PASSWORD_RESET_MINUTES}."
        )
    return minutes


def _load_frontend_url(environ: Mapping[str, str]) -> str:
    url = (environ.get(FRONTEND_URL_ENV, "").strip() or DEFAULT_FRONTEND_URL).rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ConfigError(f"{FRONTEND_URL_ENV} debe empezar por http:// o https://.")
    return url


@lru_cache
def get_settings() -> Settings:
    """Configuración del proceso, leída una sola vez. Las pruebas la reinician con cache_clear()."""
    return load_settings()
