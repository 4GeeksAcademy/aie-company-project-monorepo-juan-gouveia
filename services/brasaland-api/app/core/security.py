"""Contraseñas y tokens de acceso.

- Contraseñas: bcrypt mediante libpass (fork mantenido de passlib; se importa como `passlib`).
  El texto plano nunca se guarda ni se compara directamente.
- Tokens: JWT firmados con HS256 mediante python-jose. Solo llevan el ID del usuario (`sub`),
  la fecha de emisión (`iat`) y la de caducidad (`exp`); el rol se lee de la base en cada petición.
"""

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


def decode_access_token(token: str) -> str:
    """Valida firma, algoritmo y caducidad, y devuelve el ID del usuario (`sub`)."""
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            # Solo HS256: un token con "alg": "none" u otro algoritmo se rechaza.
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
    except ExpiredSignatureError:
        raise TokenExpiredError() from None
    except (JWTError, ValueError, TypeError):
        raise InvalidTokenError() from None

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidTokenError()
    return subject
