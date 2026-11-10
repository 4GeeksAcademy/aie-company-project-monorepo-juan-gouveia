"""Utilidades comunes de la batería unitaria de autenticación (no son fixtures)."""

import re
from contextlib import contextmanager
from datetime import datetime

import pytest

from app.core.config import Settings
from app.core.errors import ApiError
from app.domains.auth import passwords
from app.domains.auth.models import PasswordReset
from app.domains.users.database import AuthStore
from app.domains.users.models import User

PASSWORD = "parrilla-segura"
NEW_PASSWORD = "brasa-nueva-2026"

_TOKEN_IN_LINK = re.compile(r"[?&]token=([^\s&\"<]+)")


@contextmanager
def raises_api_error(status_code: int, code: str):
    """Como `pytest.raises(ApiError)`, comprobando además el estado HTTP y el código de error."""
    with pytest.raises(ApiError) as info:
        yield info
    assert (info.value.status_code, info.value.code) == (status_code, code)


def request_reset(store: AuthStore, user: User, settings: Settings, now: datetime) -> tuple[PasswordReset, str]:
    """Pide un enlace de restablecimiento como `forgot-password` y devuelve la fila y el token del enlace."""
    request = passwords.request_password_reset(store, user.email, settings, now=now)
    assert request is not None, "la solicitud debía crear un enlace"
    return request.reset, token_from_email(request.message.text)


def token_from_email(text: str) -> str:
    """Extrae el token del enlace del correo, como lo haría quien lo abre."""
    match = _TOKEN_IN_LINK.search(text)
    assert match, "el correo no contiene un enlace con token"
    return match.group(1)
