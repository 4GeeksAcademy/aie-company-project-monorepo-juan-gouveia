"""Endpoints de autenticación: login con JWT, datos del usuario autenticado y contraseñas.

La API es stateless: no hay sesiones de servidor ni cookies. Cada petición protegida lleva el token
en la cabecera `Authorization: Bearer <token>`.
"""

import json

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.email import EmailSender, get_email_sender, send_safely
from app.core.errors import ApiError
from app.core.security import create_access_token
from app.domains.auth import passwords
from app.domains.auth.dependencies import BEARER_CHALLENGE, get_current_user
from app.domains.auth.schemas import (
    FORGOT_PASSWORD_MESSAGE,
    ChangePasswordRequest,
    CurrentUser,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordChanged,
    ResetPasswordRequest,
    ResetTokenCheck,
    Token,
)
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


# --- Restablecimiento y cambio de contraseña (AUTH-03) ----------------------------------------


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    responses={422: {"description": "El email no tiene un formato válido (`invalid_request`)"}},
)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    store: AuthStore = Depends(get_auth_store),
    sender: EmailSender = Depends(get_email_sender),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    """Envía un enlace de restablecimiento si el email es de una cuenta activa.

    Responde siempre 200 con el mismo mensaje, exista o no el email, para no revelar qué cuentas
    hay. El correo sale en segundo plano, después de responder: así el tiempo de respuesta tampoco
    lo revela, y un fallo del proveedor de correo no llega al cliente (solo se registra).
    Como máximo se envían 3 enlaces por cuenta y hora; los demás se ignoran en silencio.
    """
    request = await run_in_threadpool(passwords.request_password_reset, store, data.email, settings)
    if request is not None:
        background_tasks.add_task(send_safely, sender, request.message)
    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


RESET_TOKEN_ERRORS = {
    400: {
        "description": "Enlace no válido (`invalid_reset_token`), caducado (`reset_token_expired`) "
        "o ya usado (`reset_token_used`)"
    }
}


@router.post(
    "/reset-password/validate",
    response_model=MessageResponse,
    responses={**RESET_TOKEN_ERRORS, 422: {"description": "Falta el token (`invalid_request`)"}},
)
async def validate_reset_token(data: ResetTokenCheck, store: AuthStore = Depends(get_auth_store)) -> MessageResponse:
    """Comprueba un enlace de restablecimiento sin usarlo.

    La página /reset-password lo llama al abrirse para avisar enseguida si el enlace no sirve,
    en vez de después de escribir la contraseña nueva. Mismos errores 400 que /reset-password.
    """
    try:
        await run_in_threadpool(passwords.check_reset_token, store, data.token)
    except passwords.ResetTokenError as error:
        raise ApiError(400, error.code, error.message) from None
    return MessageResponse(message="El enlace es válido.")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    responses={
        400: {
            "description": "Enlace no válido (`invalid_reset_token`), caducado (`reset_token_expired`) "
            "o ya usado (`reset_token_used`)"
        },
        422: {"description": "Falta el token o la contraseña nueva no cumple las reglas (`invalid_request`)"},
    },
)
async def reset_password(data: ResetPasswordRequest, store: AuthStore = Depends(get_auth_store)) -> MessageResponse:
    """Cambia la contraseña con el token del enlace y lo anula; las sesiones abiertas se cierran."""
    try:
        await run_in_threadpool(passwords.reset_password, store, data.token, data.new_password)
    except passwords.ResetTokenError as error:
        raise ApiError(400, error.code, error.message) from None
    return MessageResponse(message="Contraseña actualizada. Inicia sesión con tu nueva contraseña.")


@router.post(
    "/change-password",
    response_model=PasswordChanged,
    responses={
        400: {"description": "La contraseña actual no es correcta (`invalid_current_password`)"},
        401: {"description": "Falta el token o no es válido"},
        422: {"description": "La contraseña nueva no cumple las reglas (`invalid_request`)"},
    },
)
async def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    store: AuthStore = Depends(get_auth_store),
) -> PasswordChanged:
    """Cambia la contraseña del usuario autenticado, comprobando antes la actual.

    Los tokens emitidos antes dejan de valer (se cierran las sesiones de otros dispositivos); la
    respuesta trae un token nuevo para seguir en la sesión actual.
    """
    try:
        updated = await run_in_threadpool(
            passwords.change_password, store, user, data.current_password, data.new_password
        )
    except passwords.WrongCurrentPasswordError:
        raise ApiError(400, "invalid_current_password", "La contraseña actual no es correcta.") from None
    return PasswordChanged(access_token=create_access_token(updated.id))
