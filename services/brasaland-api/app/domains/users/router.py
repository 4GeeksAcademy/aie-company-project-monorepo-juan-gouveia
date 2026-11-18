"""Endpoints de gestión de usuarios (solo credenciales). Traducen HTTP y comprueban permisos;
las reglas están en service.py.

- `POST /users` es público: es el registro.
- El resto exige token. Cada usuario solo accede a su propia cuenta; un admin, a todas (403 si no).
- Listar todos los usuarios y cambiar `role` o `is_active` es solo de administradores.
"""

from fastapi import APIRouter, Depends, status

from app.core.errors import ApiError
from app.domains.auth.dependencies import ensure_self_or_admin, forbidden, get_current_user, require_admin
from app.domains.users import service
from app.domains.users.database import AuthStore
from app.domains.users.dependencies import get_auth_store
from app.domains.users.exceptions import DuplicateEmailError
from app.domains.users.models import Role, User, UserCreate, UserPublic, UserUpdate, UserWithProfile

router = APIRouter(prefix="/users", tags=["users"])

UNAUTHORIZED = {401: {"description": "Falta el token o no es válido"}}
FORBIDDEN = {403: {"description": "No es tu cuenta y no eres admin, o la cuenta está desactivada (`forbidden`)"}}
NOT_FOUND = {404: {"description": "No existe ningún usuario con ese ID (`user_not_found`)"}}
CONFLICT = {409: {"description": "Ya existe un usuario con ese email (`duplicate_email`)"}}
INVALID = {422: {"description": "Entrada inválida (`invalid_request`, con `details` por campo)"}}
ADMIN_ONLY_FIELDS = {"role", "is_active"}


def duplicate_email(error: DuplicateEmailError) -> ApiError:
    return ApiError(409, "duplicate_email", f"Ya existe un usuario con el email {error.email}.")


def not_found(user_id: str) -> ApiError:
    return ApiError(404, "user_not_found", f"No existe ningún usuario con el ID {user_id}.")


@router.post("", response_model=UserWithProfile, status_code=status.HTTP_201_CREATED, responses={**CONFLICT, **INVALID})
def register_user(data: UserCreate, store: AuthStore = Depends(get_auth_store)) -> UserWithProfile:
    """Registra un usuario con rol `user` y crea su perfil con `name`, `phone` y `address` (opcionales).

    La contraseña se guarda hasheada con bcrypt; nunca en texto plano.
    """
    try:
        user, profile = service.create_user(store, data)
    except DuplicateEmailError as error:
        raise duplicate_email(error) from None
    return UserWithProfile(**user.to_public().model_dump(), profile=profile)


@router.get(
    "",
    response_model=list[UserPublic],
    responses={**UNAUTHORIZED, 403: {"description": "Solo administradores (`forbidden`)"}},
)
def list_users(_admin: User = Depends(require_admin), store: AuthStore = Depends(get_auth_store)) -> list[UserPublic]:
    """Lista todos los usuarios. Solo administradores: incluye los emails de todas las cuentas."""
    return [user.to_public() for user in service.list_users(store)]


@router.get("/{user_id}", response_model=UserPublic, responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND})
def get_user(
    user_id: str, current: User = Depends(get_current_user), store: AuthStore = Depends(get_auth_store)
) -> UserPublic:
    """Datos de una cuenta: la propia o, si eres admin, cualquiera."""
    ensure_self_or_admin(current, user_id)
    user = service.get_user_by_id(store, user_id)
    if user is None:
        raise not_found(user_id)
    return user.to_public()


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND, **CONFLICT, **INVALID},
)
def update_user(
    user_id: str,
    data: UserUpdate,
    current: User = Depends(get_current_user),
    store: AuthStore = Depends(get_auth_store),
) -> UserPublic:
    """Actualiza las credenciales enviadas (`email`, `password`). `role` e `is_active`, solo un admin."""
    ensure_self_or_admin(current, user_id)
    if ADMIN_ONLY_FIELDS & data.model_fields_set and current.role != Role.ADMIN:
        raise forbidden("Solo un administrador puede cambiar role o is_active.")
    try:
        user = service.update_user(store, user_id, data)
    except DuplicateEmailError as error:
        raise duplicate_email(error) from None
    if user is None:
        raise not_found(user_id)
    return user.to_public()


@router.delete("/{user_id}", response_model=UserPublic, responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND})
def delete_user(
    user_id: str, current: User = Depends(get_current_user), store: AuthStore = Depends(get_auth_store)
) -> UserPublic:
    """Elimina la cuenta (la propia o, si eres admin, cualquiera) junto con su perfil, y la devuelve."""
    ensure_self_or_admin(current, user_id)
    user = service.delete_user(store, user_id)
    if user is None:
        raise not_found(user_id)
    return user.to_public()
