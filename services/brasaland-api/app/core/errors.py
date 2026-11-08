"""Formato único de errores de la API: {"error": {"code": ..., "message": ...}}.

El código es estable y legible por máquina; el mensaje está pensado para mostrarse al usuario.
Los errores de validación (422) añaden `details`: una lista de {field, message} en español.
Las rutas del gestor de incidencias responden a esos mismos errores con 400 (`BadRequestValidationRoute`),
como pide su consigna. Cualquier excepción no controlada se convierte en un 500 con un mensaje genérico:
el detalle solo queda en el log del servidor, nunca en la respuesta.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

INTERNAL_ERROR_MESSAGE = "Ha ocurrido un error inesperado. Inténtalo de nuevo más tarde."


class ApiError(Exception):
    """Error de negocio o de entrada que la API devuelve con su código HTTP."""

    def __init__(self, status_code: int, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        # Cabeceras extra de la respuesta; por ejemplo, WWW-Authenticate: Bearer en los 401.
        self.headers = headers


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error}, headers=headers)


# Mensajes en español para los errores de validación más comunes de Pydantic.
VALIDATION_MESSAGES = {
    "missing": "Campo obligatorio.",
    "extra_forbidden": "Este campo no está permitido; lo genera el sistema o no existe.",
    "greater_than": "Debe ser mayor que {gt}.",
    "float_type": "Debe ser un número.",
    "finite_number": "Debe ser un número finito.",
    "int_parsing": "Debe ser un número entero.",
    "string_type": "Debe ser un texto.",
    "string_too_short": "No puede estar vacío.",
    "string_too_long": "No puede superar {max_length} caracteres.",
    "list_type": "Debe ser una lista.",
    "too_short": "Debe tener al menos {min_length} elemento(s).",
    "enum": "Debe ser uno de estos valores: {expected}.",
    "json_invalid": "El cuerpo de la petición no es JSON válido.",
    "model_attributes_type": "El cuerpo de la petición debe ser un objeto JSON.",
    "dict_type": "El cuerpo de la petición debe ser un objeto JSON.",
}

# Prefijos de FastAPI que indican dónde estaba el dato; no forman parte del nombre del campo.
LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}


def describe_validation_errors(errors: list[dict]) -> list[dict]:
    """Convierte los errores de Pydantic en [{field, message}], con mensajes en español."""
    details = []
    for item in errors:
        parts = [str(part) for part in item["loc"]]
        if parts and parts[0] in LOCATION_PREFIXES:
            parts = parts[1:]
        field = ".".join(parts) or "body"

        kind = item["type"]
        if kind == "value_error" and str(item["msg"]).startswith("value is not a valid email address"):
            # EmailStr (email-validator) explica el fallo en inglés.
            message = "No es un email válido."
        elif kind == "value_error":
            # Validadores propios: el mensaje ya está en español; se quita el prefijo de Pydantic.
            message = str(item["msg"]).removeprefix("Value error, ")
        elif kind in VALIDATION_MESSAGES:
            ctx = dict(item.get("ctx") or {})
            if "expected" in ctx:
                # Pydantic une las opciones con "or" ('a', 'b' or 'c'); se pasa a español.
                ctx["expected"] = str(ctx["expected"]).replace(" or ", " o ")
            if isinstance(ctx.get("gt"), float) and ctx["gt"].is_integer():
                # "mayor que 0" en vez de "mayor que 0.0".
                ctx["gt"] = int(ctx["gt"])
            message = VALIDATION_MESSAGES[kind].format(**ctx)
        elif kind.startswith("value_error"):
            message = "El valor no tiene un formato válido."
        else:
            message = str(item["msg"])
        details.append({"field": field, "message": message})
    return details


async def handle_api_error(_request: Request, error: ApiError) -> JSONResponse:
    return error_response(error.status_code, error.code, error.message, headers=error.headers)


async def handle_http_exception(_request: Request, error: StarletteHTTPException) -> JSONResponse:
    # Errores propios de FastAPI (ruta inexistente, método no permitido) con el mismo formato.
    code = "not_found" if error.status_code == 404 else f"http_{error.status_code}"
    # Se conservan sus cabeceras (por ejemplo, Allow en un 405).
    return error_response(error.status_code, code, str(error.detail), headers=getattr(error, "headers", None))


def validation_error_response(error: RequestValidationError, status_code: int = 422) -> JSONResponse:
    # Datos con forma incorrecta según los esquemas de FastAPI, con el mismo formato que el resto.
    # `details` indica qué campo falló y por qué, para que el cliente pueda señalarlo.
    details = describe_validation_errors(error.errors())
    fields = ", ".join(dict.fromkeys(item["field"] for item in details))
    return error_response(status_code, "invalid_request", f"La petición no es válida. Revisa: {fields}.", details)


async def handle_validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
    return validation_error_response(error)


async def handle_unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
    # Starlette vuelve a lanzar la excepción después de esta respuesta, así que el servidor registra
    # el traceback completo en su log. Al cliente solo le llega el mensaje genérico.
    return error_response(500, "internal_error", INTERNAL_ERROR_MESSAGE)


class BadRequestValidationRoute(APIRoute):
    """Ruta cuyos errores de validación responden 400 en vez de 422, con el mismo cuerpo.

    La usa el gestor de incidencias: su consigna pide 400 con el campo problemático. El resto de la
    API mantiene el 422 de siempre.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as error:
                return validation_error_response(error, status_code=400)

        return route_handler


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
