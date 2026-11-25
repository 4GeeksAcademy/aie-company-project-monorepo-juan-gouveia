"""Dead Letter Queue: el mensaje de un fallo final y su registro en `ops.task_dead_letters` (T8 y T9).

El manejador de fallo de cada tarea de negocio publica en la cola `dead_letter` un mensaje ligero, solo con
referencias: `task_id`, nombre, intento, motivo, error, traceback, los argumentos de referencia y cuándo
falló. Nunca datos ni el informe. La tarea `dead_letters.record` lo guarda con un INSERT idempotente: si el
mensaje llega dos veces (reentrega de Redis, reintento), la segunda no hace nada.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, bindparam, text
from sqlalchemy.engine import Connection

MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
NON_RETRYABLE = "non_retryable"
REASONS = (MAX_RETRIES_EXCEEDED, NON_RETRYABLE)

# Argumentos de las tareas que pueden ir a la DLQ: solo referencias (decisión T9).
REFERENCE_ARGS = ("start", "end", "requested_by")

FIELDS = ("task_id", "task_name", "attempt", "reason", "error_message", "traceback", "task_args", "failed_at")

INSERT_SQL = text(
    """
    INSERT INTO ops.task_dead_letters
        (task_id, task_name, attempt, reason, error_message, traceback, task_args, failed_at)
    VALUES
        (:task_id, :task_name, :attempt, :reason, :error_message, :traceback, :task_args, :failed_at)
    ON CONFLICT (task_id) DO NOTHING
    """
).bindparams(bindparam("task_args", type_=JSON), bindparam("failed_at", type_=DateTime(timezone=True)))


class InvalidDeadLetter(ValueError):
    """El mensaje de la cola dead_letter no tiene la forma esperada."""


def reference_args(kwargs: dict[str, Any] | None) -> dict[str, Any]:
    """Los argumentos de la tarea que son referencias; el resto se descarta."""
    return {key: kwargs[key] for key in REFERENCE_ARGS if kwargs and key in kwargs}


def build_entry(
    *,
    task_id: str,
    task_name: str,
    attempt: int,
    reason: str,
    error_message: str,
    traceback: str | None,
    kwargs: dict[str, Any] | None,
    failed_at: datetime | None = None,
) -> dict[str, Any]:
    """El mensaje para la cola dead_letter, en JSON puro."""
    return {
        "task_id": task_id,
        "task_name": task_name,
        "attempt": attempt,
        "reason": reason,
        "error_message": error_message,
        "traceback": traceback,
        "task_args": reference_args(kwargs),
        "failed_at": (failed_at or datetime.now(UTC)).isoformat(),
    }


def validate_entry(entry: Any) -> dict[str, Any]:
    """El mensaje listo para el INSERT. Un mensaje mal formado es permanente: reintentarlo no lo arregla."""
    if not isinstance(entry, dict):
        raise InvalidDeadLetter("El mensaje de la DLQ debe ser un objeto.")
    missing = [field for field in FIELDS if field not in entry]
    if missing:
        raise InvalidDeadLetter(f"Faltan campos en el mensaje de la DLQ: {', '.join(missing)}.")
    if entry["reason"] not in REASONS:
        raise InvalidDeadLetter(f"Motivo desconocido: {entry['reason']!r}.")
    if not isinstance(entry["attempt"], int) or entry["attempt"] < 1:
        raise InvalidDeadLetter(f"Intento no válido: {entry['attempt']!r}.")
    if not isinstance(entry["task_args"], dict):
        raise InvalidDeadLetter("task_args debe ser un objeto.")
    try:
        failed_at = datetime.fromisoformat(entry["failed_at"])
    except (TypeError, ValueError) as error:
        raise InvalidDeadLetter(f"failed_at no es una fecha ISO 8601: {entry['failed_at']!r}.") from error
    if failed_at.tzinfo is None:
        failed_at = failed_at.replace(tzinfo=UTC)
    return {**{field: entry[field] for field in FIELDS}, "failed_at": failed_at}


def insert_dead_letter(connection: Connection, entry: dict[str, Any]) -> bool:
    """Guarda el fallo. True si se insertó; False si ese task_id ya estaba en la DLQ."""
    result = connection.execute(INSERT_SQL, validate_entry(entry))
    return result.rowcount == 1
