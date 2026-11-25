"""Log por tarea con las señales de Celery: una línea por cambio de estado de cada ejecución.

```
2026-11-25T10:00:01Z | INFO | telemetry.report | started | task_id=4f1c… attempt=1 | Ejecución iniciada
2026-11-25T10:00:01Z | WARNING | telemetry.report | retry | task_id=4f1c… attempt=1 duration_ms=12 | Reintento en 10 s: InjectedTransientFault: …
2026-11-25T10:00:11Z | INFO | telemetry.report | success | task_id=4f1c… attempt=2 duration_ms=240 | Terminada
2026-11-25T10:01:12Z | ERROR | telemetry.report | failure | task_id=9a0e… attempt=4 duration_ms=8 | OperationalError: … (con el traceback)
```

Mismo formato que el log de los jobs (`services/jobs/logs.py`): timestamp UTC, nivel, nombre, estado. Va a
`sys.__stderr__` (en Docker, el log del contenedor), no a `sys.stderr`: el worker redirige `sys.stderr` a
su propio logger y cada línea saldría dos veces. Nunca escribe los argumentos ni el resultado de la tarea.

Límite conocido: si se supera el límite duro (90 s), el proceso de la tarea muere y estas señales no se
emiten en él; el worker escribe el `TimeLimitExceeded` en su propio log. El límite suave (60 s) llega
antes y sí se registra.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any

from brasaland_tasks.errors import describe
from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    task_retry,
    task_success,
)

LOGGER_NAME = "brasaland.tasks"
FORMAT = "%(asctime)s | %(levelname)s | %(task_name)s | %(state)s | %(refs)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Inicio de cada ejecución en curso, por task_id, para la duración.
_started_at: dict[str, float] = {}


class _TaskFieldsDefaults(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.task_name = getattr(record, "task_name", "-")
        record.state = getattr(record, "state", "-")
        record.refs = getattr(record, "refs", "-")
        return True


def formatter() -> logging.Formatter:
    fmt = logging.Formatter(FORMAT, datefmt=DATE_FORMAT)
    fmt.converter = time.gmtime
    return fmt


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Logger de las tareas hacia el stderr real del proceso. Idempotente."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    if not any(getattr(h, "_brasaland_tasks", False) for h in logger.handlers):
        handler = logging.StreamHandler(sys.__stderr__)
        handler.setFormatter(formatter())
        handler.addFilter(_TaskFieldsDefaults())
        handler._brasaland_tasks = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def attempt_of(request: Any) -> int:
    """La ejecución en curso, desde 1 (Celery cuenta los reintentos desde 0)."""
    return int(getattr(request, "retries", 0) or 0) + 1


def _refs(task_id: str | None, attempt: int, duration_ms: int | None = None) -> str:
    refs = f"task_id={task_id} attempt={attempt}"
    return refs if duration_ms is None else f"{refs} duration_ms={duration_ms}"


def _elapsed_ms(task_id: str | None) -> int | None:
    started = _started_at.get(task_id or "")
    return None if started is None else round((time.monotonic() - started) * 1000)


def log_task(level: int, task_name: str, state: str, refs: str, message: str, **kwargs: Any) -> None:
    get_logger().log(level, message, extra={"task_name": task_name, "state": state, "refs": refs}, **kwargs)


# --- Señales ------------------------------------------------------------------------------------------


def _on_prerun(sender: Any = None, task_id: str | None = None, task: Any = None, **_: Any) -> None:
    _started_at[task_id or ""] = time.monotonic()
    log_task(logging.INFO, task.name, "started", _refs(task_id, attempt_of(task.request)), "Ejecución iniciada")


def _on_retry(sender: Any = None, request: Any = None, reason: Any = None, **_: Any) -> None:
    task_id = getattr(request, "id", None)
    # `reason` es la excepción Retry: la espera está en `when` y el error original en `exc`.
    wait = getattr(reason, "when", None)
    error = getattr(reason, "exc", None) or reason
    detail = describe(error) if isinstance(error, BaseException) else str(error)
    prefix = f"Reintento en {wait} s" if isinstance(wait, int | float) else "Reintento"
    log_task(
        logging.WARNING,
        sender.name,
        "retry",
        _refs(task_id, attempt_of(request), _elapsed_ms(task_id)),
        f"{prefix}: {detail}",
    )


def _on_success(sender: Any = None, **_: Any) -> None:
    task_id = sender.request.id
    refs = _refs(task_id, attempt_of(sender.request), _elapsed_ms(task_id))
    log_task(logging.INFO, sender.name, "success", refs, "Terminada")


def _on_failure(
    sender: Any = None, task_id: str | None = None, exception: BaseException | None = None, einfo: Any = None, **_: Any
) -> None:
    refs = _refs(task_id, attempt_of(sender.request), _elapsed_ms(task_id))
    traceback = getattr(einfo, "traceback", None)
    message = describe(exception) if exception is not None else "Fallo sin excepción"
    if traceback:
        message = f"{message}\n{traceback.rstrip()}"
    log_task(logging.ERROR, sender.name, "failure", refs, message)


def _on_postrun(sender: Any = None, task_id: str | None = None, **_: Any) -> None:
    _started_at.pop(task_id or "", None)


def connect_signals() -> None:
    """Conecta los manejadores una sola vez (dispatch_uid), aunque el módulo se importe dos veces."""
    task_prerun.connect(_on_prerun, weak=False, dispatch_uid="brasaland_tasks.logs.prerun")
    task_retry.connect(_on_retry, weak=False, dispatch_uid="brasaland_tasks.logs.retry")
    task_success.connect(_on_success, weak=False, dispatch_uid="brasaland_tasks.logs.success")
    task_failure.connect(_on_failure, weak=False, dispatch_uid="brasaland_tasks.logs.failure")
    task_postrun.connect(_on_postrun, weak=False, dispatch_uid="brasaland_tasks.logs.postrun")
