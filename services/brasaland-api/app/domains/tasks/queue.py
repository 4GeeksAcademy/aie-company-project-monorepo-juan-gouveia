"""La cola de tareas vista desde la API (ticket #DEV-55): encolar por nombre y leer el estado de Redis.

La API es solo el productor: nunca ejecuta tareas ni importa su código. Encola con `send_task` por nombre
y lee el estado del backend de resultados (Redis). Lo demás vive en dos claves propias de Redis, con la
misma duración que los resultados (24 h):

- **Dueño** (decisión T4), `brasaland:tasks:owner:{task_id}` → id de quien la encoló. Solo esa persona o
  un admin la consultan. Sin la clave, el id es desconocido (404): Celery respondería `PENDING` a
  cualquier id inventado.
- **Deduplicación** (T2 y T14), `brasaland:tasks:dedupe:{tarea}:{clave}` → `task_id`. La misma petición
  devuelve el mismo `task_id` mientras la tarea está en cola o en curso, y durante 60 s tras un `success`
  (hace de caché del informe). Tras un `failure`, o pasados esos 60 s, se encola una tarea nueva. El
  primer registro se hace con `SET NX`: dos peticiones simultáneas no encolan dos tareas.

Estados (T5), la proyección de los de Celery a los cuatro del ticket: `PENDING`, `RECEIVED` y `RETRY` →
`pending` (en cola, también esperando el countdown de un reintento); `STARTED` → `started`; `SUCCESS` →
`success`; `FAILURE` y `REVOKED` → `failure`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol
from uuid import uuid4

TaskStatusValue = Literal["pending", "started", "success", "failure"]

OWNER_KEY = "brasaland:tasks:owner:{task_id}"
DEDUPE_KEY = "brasaland:tasks:dedupe:{task_name}:{key}"
REUSE_SUCCESS_SECONDS = 60

CELERY_TO_STATUS: dict[str, TaskStatusValue] = {
    "PENDING": "pending",
    "RECEIVED": "pending",
    "RETRY": "pending",
    "STARTED": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
    "REVOKED": "failure",
}


class TaskQueueUnavailable(Exception):
    """Redis no respondió (broker o registro)."""


class RedisClient(Protocol):
    def ping(self) -> Any: ...
    def get(self, name: str) -> Any: ...
    def set(self, name: str, value: str, ex: int | None = None, nx: bool = False) -> Any: ...
    def delete(self, *names: str) -> Any: ...


@dataclass(frozen=True)
class TaskSnapshot:
    task_id: str
    status: TaskStatusValue
    result: Any


def project_state(state: str) -> TaskStatusValue:
    """El estado del ticket para un estado de Celery. Uno desconocido cuenta como en cola."""
    return CELERY_TO_STATUS.get(state, "pending")


def error_summary(error: Any) -> str:
    """El error de una tarea fallida para el cliente: tipo y primera línea, sin el SQL ni el traceback.

    El error completo queda en el log del worker y en la DLQ (`ops.task_dead_letters`).
    """
    if isinstance(error, BaseException):
        lines = str(error).strip().splitlines()
        first = lines[0] if lines else ""
        return f"{type(error).__name__}: {first}" if first else type(error).__name__
    lines = str(error).strip().splitlines() if error is not None else []
    return lines[0] if lines else "La tarea falló."


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else str(value)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _queue_errors() -> tuple[type[BaseException], ...]:
    # Errores de conexión de redis-py y de kombu (publicar en el broker), y los de red del sistema.
    from kombu.exceptions import OperationalError as KombuOperationalError
    from redis.exceptions import RedisError

    return (RedisError, KombuOperationalError, ConnectionError, OSError)


class TaskQueue:
    def __init__(
        self,
        celery_app: Any,
        redis: RedisClient,
        *,
        registry_ttl_seconds: int,
        reuse_success_seconds: int = REUSE_SUCCESS_SECONDS,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._celery = celery_app
        self._redis = redis
        self._ttl = registry_ttl_seconds
        self._reuse_success = timedelta(seconds=reuse_success_seconds)
        self._now = now or (lambda: datetime.now(UTC))

    def warm_up(self) -> None:
        """Abre ya las tres conexiones con Redis: el registro, el backend de resultados y el broker.

        Sin esto, la primera petición tras arrancar paga la conexión (unos 400 ms medidos) y el `202`
        pasaría de los 200 ms del ticket. La conexión del broker es la del pool de productores, la misma
        que usa `send_task`.
        """
        try:
            self._redis.ping()
            self._celery.backend.client.ping()
            with self._celery.producer_pool.acquire(block=True) as producer:
                producer.connection.ensure_connection(max_retries=1)
        except _queue_errors() as error:
            raise TaskQueueUnavailable(f"{type(error).__name__}: {error}") from error

    # --- Encolar --------------------------------------------------------------------------------------

    def submit(self, task_name: str, kwargs: dict[str, Any], owner_id: str, dedupe_key: str | None = None) -> str:
        """Encola la tarea (o devuelve la equivalente que sigue viva) y su `task_id`."""
        try:
            return self._submit(task_name, kwargs, owner_id, dedupe_key)
        except _queue_errors() as error:
            raise TaskQueueUnavailable(f"{type(error).__name__}: {error}") from error

    def _submit(self, task_name: str, kwargs: dict[str, Any], owner_id: str, dedupe_key: str | None) -> str:
        task_id = str(uuid4())
        key = DEDUPE_KEY.format(task_name=task_name, key=dedupe_key) if dedupe_key is not None else None
        if key is not None:
            existing = _text(self._redis.get(key))
            if existing and self._reusable(existing):
                return existing
            if existing:
                # La anterior falló, caducó o ya no sirve como caché: este registro la sustituye.
                self._redis.set(key, task_id, ex=self._ttl)
            elif not self._redis.set(key, task_id, ex=self._ttl, nx=True):
                # Otra petición igual se registró entre la lectura y la escritura: se usa la suya.
                winner = _text(self._redis.get(key))
                if winner:
                    return winner
                self._redis.set(key, task_id, ex=self._ttl)
        # El dueño se guarda antes de encolar: la primera consulta nunca puede dar 404.
        self._redis.set(OWNER_KEY.format(task_id=task_id), owner_id, ex=self._ttl)
        try:
            self._celery.send_task(task_name, kwargs=kwargs, task_id=task_id)
        except BaseException:
            # Sin mensaje en el broker, los registros apuntarían a una tarea que nunca correrá.
            names = [OWNER_KEY.format(task_id=task_id)] + ([key] if key is not None else [])
            try:
                self._redis.delete(*names)
            except _queue_errors():
                pass
            raise
        return task_id

    def _reusable(self, task_id: str) -> bool:
        if self._redis.get(OWNER_KEY.format(task_id=task_id)) is None:
            return False
        result = self._celery.AsyncResult(task_id)
        status = project_state(result.state)
        if status == "failure":
            return False
        if status == "success":
            done = result.date_done
            return done is not None and self._now() - _utc(done) <= self._reuse_success
        return True

    # --- Consultar ------------------------------------------------------------------------------------

    def owner_of(self, task_id: str) -> str | None:
        try:
            return _text(self._redis.get(OWNER_KEY.format(task_id=task_id)))
        except _queue_errors() as error:
            raise TaskQueueUnavailable(f"{type(error).__name__}: {error}") from error

    def snapshot(self, task_id: str) -> TaskSnapshot:
        try:
            result = self._celery.AsyncResult(task_id)
            status = project_state(result.state)
            value = result.result if status in ("success", "failure") else None
        except _queue_errors() as error:
            raise TaskQueueUnavailable(f"{type(error).__name__}: {error}") from error
        if status == "failure":
            value = {"error": error_summary(value)}
        return TaskSnapshot(task_id=task_id, status=status, result=value)
