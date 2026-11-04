"""Endpoints de autenticación: login con JWT y datos del usuario autenticado.

La API es stateless: no hay sesiones de servidor ni cookies. Cada petición protegida lleva el token
en la cabecera `Authorization: Bearer <token>`.
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.errors import ApiError
from app.core.security import create_access_token
from app.domains.auth.dependencies import BEARER_CHALLENGE, get_current_user
from app.domains.auth.schemas import CurrentUser, LoginRequest, Token
from app.domains.users import service
from app.domains.users.database import AuthStore
from app.domains.users.dependencies import get_auth_store
from app.domains.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

JSON_TYPES = {"application/json"}
FORM_TYPES = {"application/x-www-form-urlencoded", "multipart/form-data"}

# El cuerpo se lee a mano para aceptar JSON y formulario; esto lo documenta en /docs.
LOGIN_REQUEST_BODY = {
    "required": True,
    "content": {
        "application/json": {"schema": LoginRequest.model_json_schema()},
        "application/x-www-form-urlencoded": {
            "schema": {
                "type": "object",
                "required": ["username", "password"],
                "properties": {
                    "username": {"type": "string", "description": "Email del usuario (campo estándar de OAuth2)"},
                    "password": {"type": "string", "format": "password"},
                },
            }
        },
    },
}


async def read_credentials(request: Request) -> LoginRequest:
    """Credenciales en JSON {email, password} (briefing) o en formulario username/password.

    El formulario es el que envía el botón «Authorize» de /docs (OAuth2PasswordBearer); allí
    `username` es el email.
    """
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type in JSON_TYPES:
        try:
            payload = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise RequestValidationError(
                [{"type": "json_invalid", "loc": ("body",), "msg": "JSON inválido", "input": None}]
            ) from None
    elif content_type in FORM_TYPES:
        form = await request.form()
        payload = {"email": form.get("username") or form.get("email") or "", "password": form.get("password") or ""}
    else:
        raise ApiError(
            415, "unsupported_media_type", "Envía las credenciales en JSON {email, password} o como formulario."
        )
    try:
        return LoginRequest.model_validate(payload)
    except ValidationError as error:
        # Mismo 422 que el resto de la API, con `details` por campo.
        raise RequestValidationError(
            [{**item, "loc": ("body", *item["loc"])} for item in error.errors(include_url=False)]
        ) from None


@router.post(
    "/login",
    response_model=Token,
    openapi_extra={"requestBody": LOGIN_REQUEST_BODY},
    responses={
        401: {"description": "Email o contraseña incorrectos (`invalid_credentials`)"},
        403: {"description": "La cuenta está desactivada (`inactive_user`)"},
        415: {"description": "El cuerpo no es JSON ni formulario (`unsupported_media_type`)"},
        422: {"description": "Faltan el email o la contraseña (`invalid_request`)"},
    },
)
async def login(request: Request, store: AuthStore = Depends(get_auth_store)) -> Token:
    """Valida email y contraseña y devuelve un token JWT de acceso firmado."""
    credentials = await read_credentials(request)
    # bcrypt es lento a propósito: se ejecuta fuera del bucle de eventos.
    user = await run_in_threadpool(service.authenticate_user, store, credentials.email, credentials.password)
    if user is None:
        raise ApiError(401, "invalid_credentials", "Email o contraseña incorrectos.", headers=BEARER_CHALLENGE)
    if not user.is_active:
        raise ApiError(403, "inactive_user", "Esta cuenta está desactivada. Contacta con un administrador.")
    return Token(access_token=create_access_token(user.id))


@router.get(
    "/me",
    response_model=CurrentUser,
    responses={401: {"description": "Falta el token o no es válido"}, 403: {"description": "Cuenta desactivada"}},
)
def read_me(user: User = Depends(get_current_user), store: AuthStore = Depends(get_auth_store)) -> CurrentUser:
    """Email y rol del usuario autenticado, con su perfil vinculado (nombre y datos de contacto)."""
    return CurrentUser(id=user.id, email=user.email, role=user.role, profile=store.profiles.get_by_user_id(user.id))
