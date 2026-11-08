"""Formato único de errores de la API: {"error": {"code": ..., "message": ...}}.

El código es estable y legible por máquina; el mensaje está pensado para mostrarse al usuario.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """Error de negocio o de entrada que la API devuelve con su código HTTP."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


async def handle_api_error(_request: Request, error: ApiError) -> JSONResponse:
    return error_response(error.status_code, error.code, error.message)


async def handle_http_exception(_request: Request, error: StarletteHTTPException) -> JSONResponse:
    # Errores propios de FastAPI (ruta inexistente, método no permitido) con el mismo formato.
    code = "not_found" if error.status_code == 404 else f"http_{error.status_code}"
    return error_response(error.status_code, code, str(error.detail))


async def handle_validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
    # Datos con forma incorrecta según los esquemas de FastAPI, con el mismo formato que el resto.
    fields = ", ".join(".".join(str(part) for part in item["loc"]) for item in error.errors())
    return error_response(422, "invalid_request", f"La petición no es válida: {fields}.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
