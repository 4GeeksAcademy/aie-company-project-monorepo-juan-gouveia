"""Tareas del worker (ticket #DEV-55). Solo las carga el worker (`include` de `celery_app`); la API encola por
nombre con `send_task` y nunca importa este módulo.

**`telemetry.report`** (decisión T1): el informe técnico de telemetría, antes `GET /telemetry/report`. Se
encola con kwargs `start` y `end` (el período ya validado y resuelto por la API, ISO 8601 UTC) y
`requested_by` (id de quien lo pidió, solo como referencia para la DLQ). Devuelve el informe en JSON.

- Reintentos (T6): solo los errores transitorios (`errors.py`), con `max_retries=3` y esperas explícitas de
  10, 20 y 40 s. Los permanentes fallan a la primera.
- DLQ (T7 y T8): el fallo final, por agotar los reintentos o permanente, publica un mensaje en la cola
  `dead_letter` desde `on_failure`, que Celery llama una sola vez, cuando ya no hay más intentos.
- Timeout (T10): límites de 60 s (suave, transitorio: se reintenta) y 90 s (duro) de `celery_app`.
- Fallos forzados (T12): `TASKS_FAULT_INJECTION`, antes de tocar la base.

**`dead_letters.record`** (T8): consume la cola `dead_letter` y guarda cada mensaje en
`ops.task_dead_letters`, de forma idempotente. Si la base no responde, reintenta sin límite (esperas de 10 s
a 2 min): el mensaje espera en Redis en vez de perderse. La espera máxima queda por debajo del
`visibility_timeout` (300 s), para que Redis no reentregue el mensaje mientras el worker lo retiene.
"""

from __future__ import annotations

import logging
from typing import Any

from brasaland_tasks.celery_app import (
    DEAD_LETTER_QUEUE,
    RECORD_DEAD_LETTER_TASK,
    TELEMETRY_REPORT_TASK,
    app,
)
from brasaland_tasks.db import get_engine
from brasaland_tasks.dead_letters import (
    MAX_RETRIES_EXCEEDED,
    NON_RETRYABLE,
    build_entry,
    insert_dead_letter,
)
from brasaland_tasks.errors import describe, is_transient
from brasaland_tasks.faults import inject_fault
from brasaland_tasks.logs import (
    attempt_of,
    configure_logging,
    connect_signals,
    log_task,
)
from brasaland_tasks.report import build_report, resolve
from celery import Task

configure_logging()
connect_signals()

MAX_RETRIES = 3
RETRY_BASE_SECONDS = 10
DEAD_LETTER_RETRY_BASE_SECONDS = 10
DEAD_LETTER_MAX_WAIT_SECONDS = 120


def retry_countdown(retries: int) -> int:
    """Espera antes del siguiente intento: 10, 20 y 40 s tras el 1.º, 2.º y 3.er fallo."""
    return RETRY_BASE_SECONDS * 2**retries


def dead_letter_countdown(retries: int) -> int:
    """Espera del registro en la DLQ: 10, 20, 40, 80 y después 120 s."""
    return min(DEAD_LETTER_RETRY_BASE_SECONDS * 2**retries, DEAD_LETTER_MAX_WAIT_SECONDS)


class DeadLetterTask(Task):
    """Base de las tareas de negocio: su fallo final acaba en la cola dead_letter."""

    def on_failure(self, exc: BaseException, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        attempt = attempt_of(self.request)
        # Un transitorio que llega aquí ya agotó los reintentos; cualquier otro no se reintentó.
        reason = MAX_RETRIES_EXCEEDED if is_transient(exc) else NON_RETRYABLE
        refs = f"task_id={task_id} attempt={attempt} reason={reason}"
        entry = build_entry(
            task_id=task_id,
            task_name=self.name,
            attempt=attempt,
            reason=reason,
            error_message=describe(exc),
            traceback=getattr(einfo, "traceback", None),
            kwargs=kwargs,
        )
        try:
            record_dead_letter.apply_async(
                kwargs={"entry": entry}, queue=DEAD_LETTER_QUEUE, routing_key=DEAD_LETTER_QUEUE
            )
        except Exception as error:  # noqa: BLE001 — el fallo de la DLQ no debe tapar el de la tarea
            log_task(
                logging.CRITICAL,
                self.name,
                "dead_letter",
                refs,
                f"No se pudo publicar en la cola dead_letter ({describe(error)}); el fallo queda solo en este log: "
                f"{entry['error_message']}",
            )
            return
        log_task(logging.WARNING, self.name, "dead_letter", refs, "Enviada a la cola dead_letter")


@app.task(bind=True, base=DeadLetterTask, name=TELEMETRY_REPORT_TASK, max_retries=MAX_RETRIES)
def telemetry_report(self: Task, start: str, end: str, requested_by: str | None = None) -> dict[str, Any]:
    retries = self.request.retries
    try:
        inject_fault(retries + 1)
        start_at, end_at = resolve(start, end)
        with get_engine().connect() as connection:
            return build_report(connection, start_at, end_at)
    except Exception as error:
        if is_transient(error) and retries < self.max_retries:
            raise self.retry(exc=error, countdown=retry_countdown(retries)) from error
        raise


@app.task(bind=True, name=RECORD_DEAD_LETTER_TASK, max_retries=None)
def record_dead_letter(self: Task, entry: dict[str, Any]) -> dict[str, Any]:
    task_id = entry.get("task_id") if isinstance(entry, dict) else None
    refs = f"task_id={task_id} attempt={attempt_of(self.request)}"
    try:
        with get_engine().begin() as connection:
            inserted = insert_dead_letter(connection, entry)
    except Exception as error:
        if is_transient(error):
            raise self.retry(exc=error, countdown=dead_letter_countdown(self.request.retries)) from error
        # Permanente: la fila no se puede guardar. El log conserva lo esencial del fallo original.
        original = entry.get("error_message") if isinstance(entry, dict) else None
        log_task(
            logging.CRITICAL,
            self.name,
            "not_recorded",
            refs,
            f"No se pudo guardar en ops.task_dead_letters ({describe(error)}); fallo original: {original}",
        )
        raise
    state = "recorded" if inserted else "duplicate"
    message = "Guardada en ops.task_dead_letters" if inserted else "Ya estaba en ops.task_dead_letters"
    log_task(logging.INFO, self.name, state, refs, message)
    return {"task_id": task_id, "inserted": inserted}
