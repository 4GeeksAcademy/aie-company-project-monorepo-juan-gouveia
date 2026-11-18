"""Dependencias de autenticación y permisos.

`get_current_user` es la pieza reutilizable que protege una ruta: basta con declararla como
dependencia (en el endpoint o al registrar un router) para que la ruta exija un token válido.

- Sin token, token mal formado, firma incorrecta, caducado o de un usuario que ya no existe → 401,
  con la cabecera `WWW-Authenticate: Bearer`.
- Token válido de un usuario desactivado, o acceso a un recurso ajeno → 403.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.config import API_PREFIX
from app.core.errors import ApiError
from app.core.security import InvalidTokenError, TokenExpiredError, decode_access_token
from app.domains.users.database import AuthStore
from app.domains.users.dependencies import get_auth_store
from app.domains.users.models import Role, User

# auto_error=False: los 401 se lanzan aquí, con el formato de errores y los mensajes de la API.
# tokenUrl es la ruta que usa el botón «Authorize» de /docs para pedir el token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_PREFIX}/auth/login", auto_error=False)

BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def unauthorized(code: str, message: str) -> ApiError:
    return ApiError(401, code, message, headers=BEARER_CHALLENGE)


def forbidden(message: str) -> ApiError:
    return ApiError(403, "forbidden", message)


def get_current_user(
    token: str | None = Depends(oauth2_scheme), store: AuthStore = Depends(get_auth_store)
) -> User:
    """Extrae el Bearer de la cabecera Authorization, valida el JWT y devuelve el usuario de TinyDB."""
    if not token:
        raise unauthorized(
            "not_authenticated", "Inicia sesión: falta el token de acceso (cabecera Authorization: Bearer <token>)."
        )
    try:
        user_id = decode_access_token(token)
    except TokenExpiredError:
        raise unauthorized("token_expired", "La sesión caducó. Inicia sesión de nuevo.") from None
    except InvalidTokenError:
        raise unauthorized("invalid_token", "El token de acceso no es válido.") from None

    user = store.users.get(user_id)
    if user is None:
        # Firma válida, pero el usuario se eliminó después de emitir el token.
        raise unauthorized("invalid_token", "El token de acceso no es válido.")
    if not user.is_active:
        raise ApiError(403, "inactive_user", "Esta cuenta está desactivada. Contacta con un administrador.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Para rutas solo de administración (por ejemplo, listar todos los usuarios)."""
    if user.role != Role.ADMIN:
        raise forbidden("Solo un administrador puede hacer esta operación.")
    return user


def ensure_self_or_admin(current: User, user_id: str) -> None:
    """403 si el usuario intenta acceder a las credenciales de otro sin ser admin.

    Se comprueba antes de buscar el usuario, así un 403 no revela si ese ID existe.
    """
    if current.id != user_id and current.role != Role.ADMIN:
        raise forbidden("Solo puedes acceder a tu propia cuenta.")
