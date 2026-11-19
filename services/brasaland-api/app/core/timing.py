"""Middleware de timing: una línea de log por petición con método, ruta, estado, duración e id.

Sirve para decidir con datos qué endpoints merecen caché (ruta lenta y repetida con la misma
respuesta), no por intuición. Formato del briefing de caching, con el id de la petición al final:

    GET /api/v1/inventory/products → 200 | 312.4ms | 0f8e7d6c-5b4a-4392-8170-6e5d4c3b2a19

La duración cubre toda la petición dentro de la API (dependencias, autenticación, consulta y
serialización), no la red hasta el cliente.

Correlación (captura de telemetría, brecha B11 del plan): el backoffice crea un UUID por llamada y lo
envía en `X-Request-Id`; el BFF lo reenvía. El middleware lo usa si es un UUID válido, o crea uno si
falta o no lo es, lo devuelve en la respuesta y lo escribe en la línea de log. Así un evento de
telemetría del navegador se une con la línea de la API de la misma petición.
"""

import time
import uuid

from fastapi import FastAPI, Request

from app.core.logs import console_logger

REQUEST_ID_HEADER = "X-Request-Id"

logger = console_logger("api.timing")


def resolve_request_id(value: str | None) -> str:
    """El id recibido si es un UUID válido (normalizado en minúsculas); si no, uno nuevo.

    No se acepta cualquier texto: el valor acaba en el log y en la respuesta.
    """
    if value:
        try:
            return str(uuid.UUID(value))
        except ValueError:
            pass
    return str(uuid.uuid4())


def register_timing_middleware(app: FastAPI) -> None:
    """Registra el middleware de timing en la aplicación."""

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Un error no controlado sale de aquí antes de convertirse en el 500 de errors.py:
            # se registra igualmente, para que las peticiones fallidas también cuenten en la medición.
            duration = (time.perf_counter() - start) * 1000
            logger.info(f"{request.method} {request.url.path} → 500 | {duration:.1f}ms | {request_id}")
            raise
        duration = (time.perf_counter() - start) * 1000  # ms
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(f"{request.method} {request.url.path} → {response.status_code} | {duration:.1f}ms | {request_id}")
        return response
