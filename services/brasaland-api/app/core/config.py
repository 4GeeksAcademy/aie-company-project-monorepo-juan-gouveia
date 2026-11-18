"""Configuración que la API lee del entorno.

Los valores sensibles (la clave de firma de los JWT) y la validez del token no tienen valor por
defecto en el código: si faltan o no son válidos, la API no arranca y dice qué variable revisar.
En local se cargan desde `.env` con `uv run --env-file .env ...` (ver `.env.example`).
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


class ConfigError(RuntimeError):
    """Falta una variable de entorno obligatoria o su valor no es válido."""


@dataclass(frozen=True)
class Settings:
    # repr=False: la clave nunca aparece al imprimir la configuración ni en un traceback.
    secret_key: str = field(repr=False)
    access_token_expire_minutes: int


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

    return Settings(secret_key=secret_key, access_token_expire_minutes=minutes)


@lru_cache
def get_settings() -> Settings:
    """Configuración del proceso, leída una sola vez. Las pruebas la reinician con cache_clear()."""
    return load_settings()
