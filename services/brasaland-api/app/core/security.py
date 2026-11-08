"""Contraseñas y tokens de acceso.

- Contraseñas: bcrypt mediante libpass (fork mantenido de passlib; se importa como `passlib`).
  El texto plano nunca se guarda ni se compara directamente.
- Tokens de acceso: JWT firmados con HS256 mediante python-jose. Solo llevan el ID del usuario
  (`sub`), la fecha de emisión (`iat`) y la de caducidad (`exp`); el rol se lee de la base en cada
  petición.
- Tokens de restablecimiento de contraseña (AUTH-03): JWT con la misma firma, más `jti` (su ID en
  la tabla `password_resets`, que permite usarlos una sola vez) y `purpose: "password_reset"`.
  Un token de acceso nunca lleva `purpose`: así ninguno de los dos sirve en lugar del otro.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.hash import bcrypt

from app.core.config import get_settings

ALGORITHM = "HS256"
# bcrypt solo usa los primeros 72 bytes y la versión actual rechaza contraseñas más largas.
BCRYPT_MAX_BYTES = 72


class InvalidTokenError(Exception):
    """El token no se puede usar: mal formado, firma incorrecta o claims ausentes."""


class TokenExpiredError(InvalidTokenError):
    """El token era válido, pero ya caducó."""


PASSWORD_RESET_PURPOSE = "password_reset"


@dataclass(frozen=True)
class AccessTokenClaims:
    subject: str
    # Emisión en segundos desde epoch; se compara con `password_changed_at` del usuario.
    issued_at: int


@dataclass(frozen=True)
class PasswordResetClaims:
    subject: str
    token_id: str


# --- Contraseñas ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash bcrypt con sal aleatoria; es lo único que se guarda de la contraseña."""
    return bcrypt.hash(password)


@lru_cache
def _dummy_hash() -> str:
    return bcrypt.hash("contraseña-de-referencia-para-igualar-tiempos")


def verify_password(password: str, hashed_password: str | None) -> bool:
    """Compara la contraseña con su hash.

    Si no hay hash (el email no existe), se verifica igualmente contra un hash de referencia y se
    devuelve False: así el tiempo de respuesta no revela qué emails están registrados.
    """
    try:
        matches = bcrypt.verify(password, hashed_password or _dummy_hash())
    except (ValueError, TypeError):
        # Contraseña de más de 72 bytes o hash guardado con un formato inesperado.
        return False
    return matches and hashed_password is not None


# --- Tokens --------------------------------------------------------------------------------


def create_access_token(
    subject: str, *, expires_delta: timedelta | None = None, now: datetime | None = None
) -> str:
    """Firma un token de acceso para el usuario `subject` (su ID en TinyDB).

    La validez sale de ACCESS_TOKEN_EXPIRE_MINUTES; `expires_delta` y `now` existen para las pruebas.
    """
    settings = get_settings()
    issued_at = now or datetime.now(timezone.utc)
    lifetime = expires_delta if expires_delta is not None else timedelta(minutes=settings.access_token_expire_minutes)
    claims = {
        "sub": subject,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + lifetime).timestamp()),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def _decode(token: str, required: list[str]) -> dict:
    """Valida firma, algoritmo y caducidad, y exige los claims indicados."""
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            # Solo HS256: un token con "alg": "none" u otro algoritmo se rechaza.
            algorithms=[ALGORITHM],
            options={f"require_{name}": True for name in required},
        )
    except ExpiredSignatureError:
        raise TokenExpiredError() from None
    except (JWTError, ValueError, TypeError):
        raise InvalidTokenError() from None
    return claims


def _non_empty_str(claims: dict, name: str) -> str:
    value = claims.get(name)
    if not isinstance(value, str) or not value:
        raise InvalidTokenError()
    return value


def decode_access_token_claims(token: str) -> AccessTokenClaims:
    """Valida un token de acceso y devuelve el ID del usuario y la fecha de emisión.

    Rechaza los tokens con `purpose` (por ejemplo, un enlace de restablecimiento): no son sesiones.
    """
    claims = _decode(token, ["exp", "iat", "sub"])
    if "purpose" in claims:
        raise InvalidTokenError()
    issued_at = claims.get("iat")
    if not isinstance(issued_at, int):
        raise InvalidTokenError()
    return AccessTokenClaims(subject=_non_empty_str(claims, "sub"), issued_at=issued_at)


def decode_access_token(token: str) -> str:
    """Valida firma, algoritmo y caducidad, y devuelve el ID del usuario (`sub`)."""
    return decode_access_token_claims(token).subject


def create_password_reset_token(
    subject: str, token_id: str, *, expires_at: datetime, now: datetime | None = None
) -> str:
    """Firma el token del enlace de restablecimiento. `token_id` es el `jti` guardado en la base."""
    settings = get_settings()
    issued_at = now or datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "jti": token_id,
        "purpose": PASSWORD_RESET_PURPOSE,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def decode_password_reset_token(token: str) -> PasswordResetClaims:
    """Valida firma, caducidad y propósito. Que no se haya usado ya lo comprueba el servicio."""
    claims = _decode(token, ["exp", "iat", "sub", "jti"])
    if claims.get("purpose") != PASSWORD_RESET_PURPOSE:
        raise InvalidTokenError()
    return PasswordResetClaims(subject=_non_empty_str(claims, "sub"), token_id=_non_empty_str(claims, "jti"))
