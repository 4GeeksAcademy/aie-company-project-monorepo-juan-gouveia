"""Endpoints del perfil del usuario autenticado.

Solo existen rutas `/me`: el perfil se identifica por el token, así que nadie puede leer ni
modificar el perfil de otra persona.
"""

from fastapi import APIRouter, Depends

from app.core.errors import ApiError
from app.domains.auth.dependencies import get_current_user
from app.domains.profiles.models import Profile, ProfileUpdate
from app.domains.users.database import AuthStore
from app.domains.users.dependencies import get_auth_store
from app.domains.users.models import User

router = APIRouter(prefix="/profiles", tags=["profiles"])

RESPONSES = {
    401: {"description": "Falta el token o no es válido"},
    404: {"description": "El usuario no tiene perfil (`profile_not_found`)"},
}


def profile_not_found() -> ApiError:
    return ApiError(404, "profile_not_found", "Tu cuenta no tiene perfil. Contacta con un administrador.")


@router.get("/me", response_model=Profile, responses=RESPONSES)
def read_my_profile(user: User = Depends(get_current_user), store: AuthStore = Depends(get_auth_store)) -> Profile:
    """Perfil del usuario autenticado: nombre visible y datos de contacto."""
    profile = store.profiles.get_by_user_id(user.id)
    if profile is None:
        raise profile_not_found()
    return profile


@router.put(
    "/me",
    response_model=Profile,
    responses={**RESPONSES, 422: {"description": "Entrada inválida (`invalid_request`, con `details` por campo)"}},
)
def update_my_profile(
    data: ProfileUpdate, user: User = Depends(get_current_user), store: AuthStore = Depends(get_auth_store)
) -> Profile:
    """Actualiza `name`, `phone` y `address` del propio perfil (solo los campos enviados; `null` los vacía)."""
    profile = store.profiles.update_for_user(user.id, data)
    if profile is None:
        raise profile_not_found()
    return profile
