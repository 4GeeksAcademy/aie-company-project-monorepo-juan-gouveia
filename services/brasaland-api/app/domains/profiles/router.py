"""Endpoints de perfiles: nombre visible y datos de contacto de cada cuenta.

- `/profiles/me`: el perfil del usuario autenticado, identificado por el token.
- `/profiles/{user_id}`: el perfil de una cuenta concreta. Leerlo: el dueño o un admin.
  Modificarlo: solo el dueño ("solo el dueño del perfil puede modificarlo"), también frente a un admin.
  Cualquier otro intento responde 403.

Las rutas `/me` se declaran antes que `/{user_id}`, así "me" nunca se interpreta como un ID.
"""

from fastapi import APIRouter, Depends

from app.core.errors import ApiError
from app.domains.auth.dependencies import ensure_self_or_admin, forbidden, get_current_user
from app.domains.profiles.models import Profile, ProfileUpdate
from app.domains.users.database import AuthStore
from app.domains.users.dependencies import get_auth_store
from app.domains.users.models import User

router = APIRouter(prefix="/profiles", tags=["profiles"])

RESPONSES = {
    401: {"description": "Falta el token o no es válido"},
    404: {"description": "El usuario no tiene perfil (`profile_not_found`)"},
}
INVALID = {422: {"description": "Entrada inválida (`invalid_request`, con `details` por campo)"}}


def profile_not_found() -> ApiError:
    return ApiError(404, "profile_not_found", "Esa cuenta no tiene perfil. Contacta con un administrador.")


def read_profile(store: AuthStore, user_id: str) -> Profile:
    profile = store.profiles.get_by_user_id(user_id)
    if profile is None:
        raise profile_not_found()
    return profile


def write_profile(store: AuthStore, user_id: str, data: ProfileUpdate) -> Profile:
    profile = store.profiles.update_for_user(user_id, data)
    if profile is None:
        raise profile_not_found()
    return profile


@router.get("/me", response_model=Profile, responses=RESPONSES)
def read_my_profile(user: User = Depends(get_current_user), store: AuthStore = Depends(get_auth_store)) -> Profile:
    """Perfil del usuario autenticado: nombre visible y datos de contacto."""
    return read_profile(store, user.id)


@router.put("/me", response_model=Profile, responses={**RESPONSES, **INVALID})
def update_my_profile(
    data: ProfileUpdate, user: User = Depends(get_current_user), store: AuthStore = Depends(get_auth_store)
) -> Profile:
    """Actualiza `name`, `phone` y `address` del propio perfil (solo los campos enviados; `null` los vacía)."""
    return write_profile(store, user.id, data)


@router.get(
    "/{user_id}",
    response_model=Profile,
    responses={**RESPONSES, 403: {"description": "No es tu perfil y no eres admin (`forbidden`)"}},
)
def read_profile_by_user(
    user_id: str, current: User = Depends(get_current_user), store: AuthStore = Depends(get_auth_store)
) -> Profile:
    """Perfil de una cuenta por el `id` de su usuario: el propio o, si eres admin, cualquiera."""
    ensure_self_or_admin(current, user_id)
    return read_profile(store, user_id)


@router.put(
    "/{user_id}",
    response_model=Profile,
    responses={**RESPONSES, **INVALID, 403: {"description": "No es tu perfil (`forbidden`), también para un admin"}},
)
def update_profile_by_user(
    user_id: str,
    data: ProfileUpdate,
    current: User = Depends(get_current_user),
    store: AuthStore = Depends(get_auth_store),
) -> Profile:
    """Actualiza un perfil por el `id` de su usuario. Solo el dueño puede modificarlo."""
    if current.id != user_id:
        raise forbidden("Solo el dueño del perfil puede modificarlo.")
    return write_profile(store, user_id, data)
