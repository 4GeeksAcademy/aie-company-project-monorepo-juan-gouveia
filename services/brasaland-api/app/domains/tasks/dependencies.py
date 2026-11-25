"""La cola de tareas como dependencia de FastAPI; las pruebas la sustituyen con `dependency_overrides`.

Se crea la primera vez que una ruta la pide, no al importar ni al arrancar: `brasaland_tasks.celery_app`
exige `REDIS_URL` al importarse, y sin ella la API debe seguir sirviendo el resto de sus rutas. Las dos
rutas de la cola responden entonces `503 task_queue_unavailable` (y el arranque lo avisa en el log).
"""

import os
from functools import lru_cache

from app.core.errors import ApiError
from app.core.logs import console_logger
from app.domains.tasks.queue import TaskQueue

REDIS_URL_ENV = "REDIS_URL"
# Una consulta de estado o un encolado no deben colgar la petición si Redis no responde.
REDIS_TIMEOUT_SECONDS = 2

logger = console_logger("api.tasks")


def queue_configured() -> bool:
    return bool(os.environ.get(REDIS_URL_ENV, "").strip())


def queue_unavailable() -> ApiError:
    return ApiError(
        503, "task_queue_unavailable", "La cola de tareas no está disponible en este momento. Vuelve a intentarlo."
    )


@lru_cache(maxsize=1)
def _default_queue() -> TaskQueue:
    # Importación diferida: crea la aplicación de Celery (y exige REDIS_URL) solo cuando hace falta.
    from brasaland_tasks.celery_app import app as celery_app
    from brasaland_tasks.celery_app import redis_url
    from brasaland_tasks.names import RESULT_EXPIRES_SECONDS
    from redis import Redis

    redis = Redis.from_url(
        redis_url(), socket_connect_timeout=REDIS_TIMEOUT_SECONDS, socket_timeout=REDIS_TIMEOUT_SECONDS
    )
    return TaskQueue(celery_app, redis, registry_ttl_seconds=RESULT_EXPIRES_SECONDS)


def get_task_queue() -> TaskQueue:
    try:
        return _default_queue()
    except RuntimeError as error:
        # MissingRedisUrl (falta o no es redis://). lru_cache no guarda las excepciones: cuando se
        # configure, la siguiente petición la crea.
        logger.error(f"Cola de tareas no configurada: {error}")
        raise queue_unavailable() from error
