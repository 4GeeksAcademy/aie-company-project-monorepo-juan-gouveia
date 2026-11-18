"""Restablecimiento y cambio de contraseña (ticket AUTH-03).

- Solicitud: si el email es de un usuario activo y no superó el límite por hora, se crea un enlace
  (fila en `password_resets` + JWT firmado) y se prepara el correo. Si no, no pasa nada: el router
  responde igual en todos los casos, para no revelar qué emails están registrados.
- Restablecimiento: el token debe tener firma válida, no haber caducado, tener el propósito correcto
  y no haberse usado. Al usarlo se anulan todos los enlaces pendientes del usuario.
- Cambio: exige la contraseña actual.

En ambos casos se guarda `password_changed_at`, que invalida los tokens de acceso emitidos antes.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import Settings
from app.core.email import EmailMessage
from app.core.security import (
    InvalidTokenError,
    TokenExpiredError,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
)
from app.domains.auth.emails import build_password_reset_email
from app.domains.auth.models import PasswordReset
from app.domains.users.database import AuthStore
from app.domains.users.models import User
from app.domains.users.service import get_user_by_email

# Opcional "rate limiting" del ticket (decisión P-9): solicitudes por usuario y hora.
MAX_RESET_REQUESTS_PER_HOUR = 3
RESET_PATH = "/reset-password"


class ResetTokenError(Exception):
    """El enlace no sirve. `code` distingue el motivo; el router responde 400 en todos los casos."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


INVALID_TOKEN = ("invalid_reset_token", "El enlace de restablecimiento no es válido. Solicita uno nuevo.")
EXPIRED_TOKEN = ("reset_token_expired", "El enlace de restablecimiento ha caducado. Solicita uno nuevo.")
USED_TOKEN = ("reset_token_used", "Este enlace de restablecimiento ya se usó. Solicita uno nuevo si lo necesitas.")


class WrongCurrentPasswordError(Exception):
    """La contraseña actual no coincide."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _whole_seconds(moment: datetime) -> datetime:
    """`iat` va en segundos enteros: un token emitido justo después del cambio debe seguir valiendo."""
    return moment.replace(microsecond=0)


def is_token_revoked(user: User, issued_at: int) -> bool:
    """True si el token de acceso se emitió antes del último cambio de contraseña."""
    if user.password_changed_at is None:
        return False
    return issued_at < int(user.password_changed_at.timestamp())


@dataclass(frozen=True)
class ResetRequest:
    reset: PasswordReset
    message: EmailMessage


def request_password_reset(
    store: AuthStore, email: str, settings: Settings, now: datetime | None = None
) -> ResetRequest | None:
    """Crea el enlace y su correo, o None si no hay que enviar nada (sin revelar el motivo)."""
    now = now or _now()
    user = get_user_by_email(store, email)
    if user is None or not user.is_active:
        return None

    lifetime = timedelta(minutes=settings.password_reset_expire_minutes)
    reset = PasswordReset(id=str(uuid.uuid4()), user_id=user.id, created_at=now, expires_at=now + lifetime)
    with store.lock:
        recent = store.password_resets.count_created_since(user.id, now - timedelta(hours=1))
        if recent >= MAX_RESET_REQUESTS_PER_HOUR:
            return None
        store.password_resets.insert(reset)

    token = create_password_reset_token(user.id, reset.id, expires_at=reset.expires_at, now=now)
    profile = store.profiles.get_by_user_id(user.id)
    message = build_password_reset_email(
        to=user.email,
        name=profile.name if profile else None,
        link=f"{settings.frontend_url}{RESET_PATH}?token={token}",
        expire_minutes=settings.password_reset_expire_minutes,
    )
    return ResetRequest(reset=reset, message=message)


def _decode_reset_token(token: str):
    try:
        return decode_password_reset_token(token)
    except TokenExpiredError:
        raise ResetTokenError(*EXPIRED_TOKEN) from None
    except InvalidTokenError:
        raise ResetTokenError(*INVALID_TOKEN) from None


def _usable_reset(store: AuthStore, token_id: str, user_id: str, now: datetime) -> User:
    """Comprueba que el enlace existe, es de ese usuario, no se usó ni caducó. Requiere el bloqueo."""
    reset = store.password_resets.get(token_id)
    if reset is None or reset.user_id != user_id:
        raise ResetTokenError(*INVALID_TOKEN)
    if reset.used_at is not None:
        raise ResetTokenError(*USED_TOKEN)
    if reset.expires_at <= now:
        raise ResetTokenError(*EXPIRED_TOKEN)
    user = store.users.get(user_id)
    if user is None or not user.is_active:
        raise ResetTokenError(*INVALID_TOKEN)
    return user


def check_reset_token(store: AuthStore, token: str, now: datetime | None = None) -> None:
    """Comprueba el enlace sin usarlo, para avisar al abrir la página. Lanza ResetTokenError si no sirve."""
    now = now or _now()
    claims = _decode_reset_token(token)
    with store.lock:
        _usable_reset(store, claims.token_id, claims.subject, now)


def reset_password(store: AuthStore, token: str, new_password: str, now: datetime | None = None) -> User:
    """Cambia la contraseña con un enlace válido y lo anula. Lanza ResetTokenError si no sirve."""
    now = _whole_seconds(now or _now())
    claims = _decode_reset_token(token)

    # bcrypt es lento: el hash se calcula fuera del bloqueo.
    hashed = hash_password(new_password)
    with store.lock:
        user = _usable_reset(store, claims.token_id, claims.subject, now)
        updated = store.users.update(
            user.id, {"hashed_password": hashed, "password_changed_at": now.isoformat()}
        )
        if updated is None:
            raise ResetTokenError(*INVALID_TOKEN)
        # Anula este enlace y cualquier otro pendiente del mismo usuario.
        store.password_resets.mark_all_used(user.id, now)
    return updated


def change_password(
    store: AuthStore, user: User, current_password: str, new_password: str, now: datetime | None = None
) -> User:
    """Cambia la contraseña de un usuario autenticado. Lanza WrongCurrentPasswordError si no coincide."""
    now = _whole_seconds(now or _now())
    if not verify_password(current_password, user.hashed_password):
        raise WrongCurrentPasswordError()
    hashed = hash_password(new_password)
    with store.lock:
        updated = store.users.update(
            user.id, {"hashed_password": hashed, "password_changed_at": now.isoformat()}
        )
        # Un enlace de restablecimiento pedido antes ya no debe servir.
        store.password_resets.mark_all_used(user.id, now)
    if updated is None:
        # El usuario se borró entre la autenticación y el cambio.
        raise WrongCurrentPasswordError()
    return updated
