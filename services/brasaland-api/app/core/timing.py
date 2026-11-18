"""Middleware de timing: una línea de log por petición con método, ruta, estado y duración.

Sirve para decidir con datos qué endpoints merecen caché (ruta lenta y repetida con la misma
respuesta), no por intuición. Formato del briefing de caching:

    GET /api/v1/inventory/products → 200 | 312.4ms

La duración cubre toda la petición dentro de la API (dependencias, autenticación, consulta y
serialización), no la red hasta el cliente.
"""

import logging
import time

from fastapi import FastAPI, Request

logger = logging.getLogger("api.timing")


def _configure_logger() -> None:
    # Uvicorn solo configura sus propios loggers: sin un handler, las líneas de INFO de "api.timing"
    # no saldrían por consola. Se añade una sola vez, aunque se registre el middleware varias veces.
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def register_timing_middleware(app: FastAPI) -> None:
    """Registra el middleware de timing en la aplicación."""
    _configure_logger()

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Un error no controlado sale de aquí antes de convertirse en el 500 de errors.py:
            # se registra igualmente, para que las peticiones fallidas también cuenten en la medición.
            duration = (time.perf_counter() - start) * 1000
            logger.info(f"{request.method} {request.url.path} → 500 | {duration:.1f}ms")
            raise
        duration = (time.perf_counter() - start) * 1000  # ms
        logger.info(f"{request.method} {request.url.path} → {response.status_code} | {duration:.1f}ms")
        return response
