"""Instancia de Celery de Brasaland (ticket #DEV-55): Redis como broker y como backend de resultados.

La API (productor) encola con `send_task` por nombre y nunca ejecuta tareas; el worker (consumidor) es un
proceso aparte que escucha las colas:

    celery -A brasaland_tasks.celery_app worker -Q default,dead_letter --loglevel=INFO

En Windows, fuera de Docker, con `--pool=solo` (el pool por defecto, prefork, no funciona en Windows).

La conexión sale solo de `REDIS_URL`, la misma en la API, el worker y Flower. Sin ella, nada arranca: un
broker por defecto (`amqp://localhost`) fallaría más tarde y con un error menos claro.

Configuración (decisión T10 del plan):

- **ACK solo tras éxito:** `task_acks_late` y `task_reject_on_worker_lost`. Si el worker cae a mitad de una
  tarea, el mensaje vuelve a la cola. Con Redis, tras un corte brusco vuelve al pasar `visibility_timeout`.
- **De uno en uno:** `worker_prefetch_multiplier = 1`; el worker no acapara mensajes que no está procesando.
- **Toda tarea tiene timeout:** 60 s el límite suave (excepción dentro de la tarea, que se reintenta) y 90 s
  el duro (se mata la ejecución).
- **`visibility_timeout` de 300 s:** más que la mayor espera de reintento (40 s) más el límite duro (90 s).
  Si fuera menor, Redis reentregaría tareas que siguen vivas y se ejecutarían dos veces.
- **Mensajes ligeros y seguros:** solo JSON (sin `pickle`, que ejecuta código al deserializar).
- **Estados reales:** `task_track_started` para que exista `STARTED`; los resultados duran 24 h.
- **Flower:** el worker emite eventos y el productor el de "enviada", para ver las tareas en cola.
"""

from __future__ import annotations

import os

from celery import Celery
from kombu import Exchange, Queue

APP_NAME = "brasaland"

# Colas: `default` para las tareas de negocio y `dead_letter` para los fallos finales (decisión T8).
DEFAULT_QUEUE = "default"
DEAD_LETTER_QUEUE = "dead_letter"

SOFT_TIME_LIMIT_SECONDS = 60
TIME_LIMIT_SECONDS = 90
VISIBILITY_TIMEOUT_SECONDS = 300
RESULT_EXPIRES_SECONDS = 24 * 60 * 60
WORKER_CONCURRENCY = 2


class MissingRedisUrl(RuntimeError):
    """Falta la variable de entorno REDIS_URL."""


def redis_url() -> str:
    """La URL de Redis de `REDIS_URL` (p. ej. `redis://localhost:6379/0`). Sin ella, error explícito."""
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        raise MissingRedisUrl(
            "Falta REDIS_URL: la URL de Redis, broker y backend de la cola de tareas "
            "(redis://localhost:6379/0 fuera de Docker, redis://redis:6379/0 dentro de la red de Compose)."
        )
    if not url.startswith(("redis://", "rediss://")):
        raise MissingRedisUrl("REDIS_URL debe empezar por redis:// o rediss://.")
    return url


def _queue(name: str) -> Queue:
    """Una cola con su propio exchange y su propia routing key.

    Sin ellos, Celery enlaza todas las colas de `task_queues` al exchange `default` con la clave `default`,
    y cada mensaje de `default` se copiaría también en `dead_letter`.
    """
    return Queue(name, Exchange(name, type="direct"), routing_key=name)


def create_app(url: str) -> Celery:
    """La aplicación de Celery con Redis en `url` como broker y como backend de resultados."""
    app = Celery(APP_NAME, broker=url, backend=url)
    transport_options = {"visibility_timeout": VISIBILITY_TIMEOUT_SECONDS}
    app.conf.update(
        # Serialización: solo JSON.
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # ACK tras éxito y reparto de uno en uno.
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        worker_concurrency=WORKER_CONCURRENCY,
        # Toda tarea tiene timeout.
        task_soft_time_limit=SOFT_TIME_LIMIT_SECONDS,
        task_time_limit=TIME_LIMIT_SECONDS,
        broker_transport_options=transport_options,
        result_backend_transport_options=transport_options,
        # Estados y resultados.
        task_track_started=True,
        result_expires=RESULT_EXPIRES_SECONDS,
        # Colas.
        task_default_queue=DEFAULT_QUEUE,
        task_queues=[_queue(DEFAULT_QUEUE), _queue(DEAD_LETTER_QUEUE)],
        # Si Redis aún no está listo al arrancar, el worker espera en vez de caerse.
        broker_connection_retry_on_startup=True,
        # Eventos para Flower: tareas enviadas (en cola), en proceso y terminadas.
        worker_send_task_events=True,
        task_send_sent_event=True,
        # Fechas en UTC, como el resto del monorepo.
        enable_utc=True,
        timezone="UTC",
    )
    return app


app = create_app(redis_url())
