"""Control de estado de los jobs programados: `ops.job_runs` (migración 006, ticket #DEV-53).

Cada ejecución sigue la máquina de estados del ticket:

    pending → processing → completed
                        ↘ failed

- **pending:** el registro se crea antes de empezar.
- **processing:** se escribe antes de hacer ningún trabajo. Es el lock: el índice único parcial
  `uq_job_runs_one_processing` admite una sola fila `processing` por job, así que la transición falla de
  forma atómica si otra instancia ya lo tiene, aunque las dos hayan pasado `has_processing_lock` en el
  mismo instante (decisión N9). No hay tabla ni columna de lock aparte.
- **completed / failed:** cierran la ejecución y liberan el lock. Un `try/except/finally` en `run_job`
  garantiza que ninguna fila se quede en `processing` por una excepción; si el proceso muere sin pasar
  por el `finally` (un kill), la siguiente ejecución la cierra como `abandoned` (decisión N11).

La omisión por duplicado y la cancelación por lock no crean fila: solo se registran en el log, de modo
que ejecutar dos veces deja `job_runs` igual que una (decisión N10). La instancia que pierde la carrera
del índice ya había creado su fila `pending`: la cierra como `failed` con `lock_held: …`.

`run_job` abre una transacción por paso: cada estado queda escrito (y visible para otras instancias)
antes del siguiente. El mismo SQL funciona en PostgreSQL (Supabase) y en SQLite (pruebas).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Engine,
    Index,
    MetaData,
    Table,
    Text,
    Uuid,
    create_engine,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from brasaland_jobs.logs import get_logger

JOB_STATUSES = ("pending", "processing", "completed", "failed")
OPEN_STATUSES = ("pending", "processing")
DEFAULT_STALE_MINUTES = 120
ERROR_MESSAGE_MAX_LENGTH = 2000

# --- Tabla (la de la migración 006) ---------------------------------------------------------------

metadata = MetaData(schema="ops")

job_runs = Table(
    "job_runs",
    metadata,
    Column("id", Uuid, primary_key=True, default=uuid4),
    Column("job_name", Text, nullable=False),
    Column("target_date", Date, nullable=False),
    Column("status", Text, nullable=False, server_default="pending"),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("error_message", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="job_runs_status_check"),
    CheckConstraint("status <> 'processing' OR started_at IS NOT NULL", name="job_runs_processing_started"),
    CheckConstraint(
        "status NOT IN ('completed', 'failed') OR finished_at IS NOT NULL", name="job_runs_finished_when_closed"
    ),
    CheckConstraint("status <> 'completed' OR error_message IS NULL", name="job_runs_completed_without_error"),
    CheckConstraint("status <> 'failed' OR error_message IS NOT NULL", name="job_runs_failed_with_error"),
    CheckConstraint(
        "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at", name="job_runs_finished_after_start"
    ),
    Index("idx_job_runs_job_name_target_date", "job_name", "target_date"),
    Index(
        "uq_job_runs_one_processing",
        "job_name",
        unique=True,
        postgresql_where=text("status = 'processing'"),
        sqlite_where=text("status = 'processing'"),
    ),
)


class LockHeld(RuntimeError):
    """Otra instancia del job tiene una fila en `processing` (índice único parcial de la 006)."""


class JobRunNotOpen(RuntimeError):
    """La fila ya no está en el estado que exige la transición (o no existe)."""


class JobOutcome(StrEnum):
    """Cómo terminó `run_job` sin excepción. Un fallo no es un resultado: se propaga."""

    COMPLETED = "completed"
    SKIPPED_DUPLICATE = "skipped"  # ya había una ejecución completed para (job_name, target_date)
    CANCELLED_LOCK = "cancelled"  # otra instancia tenía el job en processing


def utcnow() -> datetime:
    return datetime.now(UTC)


# --- Conexión -------------------------------------------------------------------------------------


def with_psycopg2_driver(url: str) -> str:
    """La cadena tal como la copia Supabase (`postgresql://...`), con el driver psycopg2 explícito.

    SQLAlchemy 2.1 usa por defecto psycopg (v3) para `postgresql://`, que no está instalado. Lo mismo
    hacen la API (`app.core.database`) y el pipeline (`brasaland_pipelines.repository`).
    """
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            return "postgresql+psycopg2://" + url.removeprefix(scheme)
    return url


def create_jobs_engine(url: str) -> Engine:
    """Motor de SQLAlchemy para la cadena del rol `nightly_jobs` (`JOBS_DATABASE_URL`)."""
    return create_engine(with_psycopg2_driver(url), pool_pre_ping=True)


# --- Consultas ------------------------------------------------------------------------------------


def has_processing_lock(conn: Connection, job_name: str) -> bool:
    """¿Hay una ejecución de este job en `processing`? Es el lock (de cualquier `target_date`)."""
    query = select(job_runs.c.id).where(job_runs.c.job_name == job_name, job_runs.c.status == "processing")
    return conn.execute(query.limit(1)).first() is not None


def has_completed_for_date(conn: Connection, job_name: str, target_date: date) -> bool:
    """¿Ya hay una ejecución `completed` de este job para esta fecha? La clave de idempotencia."""
    query = select(job_runs.c.id).where(
        job_runs.c.job_name == job_name,
        job_runs.c.target_date == target_date,
        job_runs.c.status == "completed",
    )
    return conn.execute(query.limit(1)).first() is not None


def get_run(conn: Connection, run_id: UUID) -> dict[str, Any] | None:
    row = conn.execute(select(job_runs).where(job_runs.c.id == run_id)).mappings().first()
    return dict(row) if row else None


def list_runs(conn: Connection, job_name: str, target_date: date | None = None) -> list[dict[str, Any]]:
    """Las ejecuciones de un job (de una fecha, si se indica), de la más antigua a la más reciente."""
    query = select(job_runs).where(job_runs.c.job_name == job_name)
    if target_date is not None:
        query = query.where(job_runs.c.target_date == target_date)
    return [dict(row) for row in conn.execute(query.order_by(job_runs.c.created_at, job_runs.c.id)).mappings()]


# --- Transiciones ---------------------------------------------------------------------------------


def create_run(conn: Connection, job_name: str, target_date: date, *, now: datetime) -> UUID:
    """Crea la ejecución en `pending`, antes de empezar."""
    run_id = uuid4()
    conn.execute(
        insert(job_runs).values(id=run_id, job_name=job_name, target_date=target_date, status="pending", created_at=now)
    )
    return run_id


def start_run(conn: Connection, run_id: UUID, *, now: datetime) -> None:
    """`pending → processing`, antes de hacer ningún trabajo. `LockHeld` si otra instancia tiene el lock.

    Quien llama debe confirmar la transacción enseguida: el lock solo protege cuando es visible.
    """
    statement = (
        update(job_runs)
        .where(job_runs.c.id == run_id, job_runs.c.status == "pending")
        .values(status="processing", started_at=now)
    )
    try:
        result = conn.execute(statement)
    except IntegrityError as error:
        raise LockHeld("Otra instancia tiene el job en processing.") from error
    if result.rowcount != 1:
        raise JobRunNotOpen(f"La ejecución {run_id} no está en pending.")


def complete_run(conn: Connection, run_id: UUID, *, now: datetime) -> None:
    """`processing → completed`: solo si todo terminó bien. Libera el lock."""
    statement = (
        update(job_runs)
        .where(job_runs.c.id == run_id, job_runs.c.status == "processing")
        .values(status="completed", finished_at=now, error_message=None)
    )
    if conn.execute(statement).rowcount != 1:
        raise JobRunNotOpen(f"La ejecución {run_id} no está en processing.")


def fail_run(conn: Connection, run_id: UUID, error_message: str, *, now: datetime) -> bool:
    """`pending | processing → failed`, con el mensaje. Libera el lock.

    Devuelve False si la fila ya estaba cerrada (p. ej., otra instancia la cerró como abandonada).
    """
    statement = (
        update(job_runs)
        .where(job_runs.c.id == run_id, job_runs.c.status.in_(OPEN_STATUSES))
        .values(status="failed", finished_at=now, error_message=_truncate(error_message))
    )
    return conn.execute(statement).rowcount == 1


def abandon_stale_runs(conn: Connection, job_name: str, *, now: datetime, stale_minutes: int) -> list[dict[str, Any]]:
    """Cierra como `failed` ('abandoned: …') las ejecuciones abiertas más antiguas que `stale_minutes`.

    Un proceso que muere sin pasar por el `finally` (SIGKILL, falta de memoria, corte de luz) deja su
    fila en `processing`: sin esto, el lock quedaría tomado para siempre y todas las noches siguientes se
    cancelarían en silencio. Cuenta desde `started_at` (o `created_at` si nunca llegó a processing).
    Devuelve las filas cerradas, para registrarlas en el log.
    """
    threshold = now - timedelta(minutes=stale_minutes)
    condition = (
        (job_runs.c.job_name == job_name)
        & job_runs.c.status.in_(OPEN_STATUSES)
        & (func.coalesce(job_runs.c.started_at, job_runs.c.created_at) < threshold)
    )
    stale = [dict(row) for row in conn.execute(select(job_runs).where(condition)).mappings()]
    for row in stale:
        message = (
            f"abandoned: seguía en {row['status']} después de {stale_minutes} min; "
            "el proceso terminó sin cerrar la ejecución"
        )
        conn.execute(
            update(job_runs)
            .where(job_runs.c.id == row["id"], job_runs.c.status.in_(OPEN_STATUSES))
            .values(status="failed", finished_at=now, error_message=message)
        )
    return stale


# --- Orquestación de una ejecución ----------------------------------------------------------------


def run_job(
    engine: Engine,
    job_name: str,
    target_date: date,
    work: Callable[[], None],
    *,
    stale_minutes: int = DEFAULT_STALE_MINUTES,
    clock: Callable[[], datetime] = utcnow,
    logger: logging.Logger | None = None,
) -> JobOutcome:
    """Ejecuta `work` una sola vez por `(job_name, target_date)`, con la máquina de estados completa.

    1. Cierra las ejecuciones abandonadas (N11).
    2. Omisión por duplicado si ya hay una `completed` para la fecha, y cancelación si otra instancia
       tiene el job en `processing`: solo en el log, sin fila (N10).
    3. `pending`, y `processing` antes de llamar a `work` (el lock).
    4. `completed` si `work` termina bien; `failed` con el mensaje ante cualquier excepción (incluidas
       `KeyboardInterrupt` y `SystemExit`), que se registra en el log con su traza y se propaga.
    """
    log = _JobLog(logger or get_logger(), job_name, target_date)

    with engine.begin() as conn:
        abandoned = abandon_stale_runs(conn, job_name, now=clock(), stale_minutes=stale_minutes)
    for row in abandoned:
        log.error("failed", f"Ejecución {row['id']} cerrada como abandoned (seguía en {row['status']})")

    with engine.begin() as conn:
        if has_completed_for_date(conn, job_name, target_date):
            log.info(JobOutcome.SKIPPED_DUPLICATE, "Omitida por duplicado: ya hay una ejecución completed para esta fecha")
            return JobOutcome.SKIPPED_DUPLICATE
        if has_processing_lock(conn, job_name):
            log.info(JobOutcome.CANCELLED_LOCK, "Cancelada: otra instancia tiene el job en processing")
            return JobOutcome.CANCELLED_LOCK

    with engine.begin() as conn:
        run_id = create_run(conn, job_name, target_date, now=clock())
    log.info("pending", f"Ejecución {run_id} registrada")

    try:
        with engine.begin() as conn:
            start_run(conn, run_id, now=clock())
    except LockHeld:
        # Perdió la carrera del índice: otra instancia pasó a processing entre la comprobación y aquí.
        with engine.begin() as conn:
            fail_run(conn, run_id, f"lock_held: otra instancia tiene {job_name} en processing", now=clock())
        log.info(JobOutcome.CANCELLED_LOCK, f"Cancelada: otra instancia tomó el lock primero (ejecución {run_id} cerrada)")
        return JobOutcome.CANCELLED_LOCK
    except BaseException as error:
        _close_failed(engine, run_id, error, clock, log)
        raise

    log.info("processing", f"Inicio de la ejecución {run_id}")
    started = time.monotonic()
    closed = False
    error: BaseException | None = None
    try:
        work()
        with engine.begin() as conn:
            complete_run(conn, run_id, now=clock())
        closed = True
        log.info("completed", f"Fin de la ejecución {run_id} en {time.monotonic() - started:.1f} s")
        return JobOutcome.COMPLETED
    except BaseException as exc:
        error = exc
        raise
    finally:
        # La garantía del ticket: ninguna fila se queda en processing por una excepción.
        if not closed:
            _close_failed(engine, run_id, error, clock, log)


def _close_failed(
    engine: Engine, run_id: UUID, error: BaseException | None, clock: Callable[[], datetime], log: _JobLog
) -> None:
    message = error_message_of(error) if error is not None else "interrupted: la ejecución terminó sin resultado"
    exc_info = (type(error), error, error.__traceback__) if error is not None else None
    try:
        with engine.begin() as conn:
            fail_run(conn, run_id, message, now=clock())
    except Exception as db_error:  # noqa: BLE001 — no debe tapar el error original
        log.error(
            "processing",
            f"Ejecución {run_id}: no se pudo marcar failed ({error_message_of(db_error)}); "
            "la próxima ejecución la cerrará como abandoned. Error original: " + message,
            exc_info=exc_info,
        )
        return
    log.error("failed", f"Ejecución {run_id} fallida: {message}", exc_info=exc_info)


def error_message_of(error: BaseException) -> str:
    """`Tipo: mensaje` de la excepción, recortado; solo el tipo si no tiene mensaje."""
    detail = str(error).strip()
    return _truncate(f"{type(error).__name__}: {detail}" if detail else type(error).__name__)


def _truncate(message: str) -> str:
    if len(message) <= ERROR_MESSAGE_MAX_LENGTH:
        return message
    return message[: ERROR_MESSAGE_MAX_LENGTH - 1] + "…"


class _JobLog:
    """Cada línea con el nombre del job, el estado resultante y la fecha objetivo (formato en `logs.py`)."""

    def __init__(self, logger: logging.Logger, job_name: str, target_date: date) -> None:
        self._logger = logger
        self._job = job_name
        self._target_date = target_date

    def _log(self, level: int, status: str, message: str, exc_info: Any = None) -> None:
        self._logger.log(
            level,
            f"target_date={self._target_date.isoformat()} | {message}",
            extra={"job": self._job, "status": str(status)},
            exc_info=exc_info,
        )

    def info(self, status: str, message: str) -> None:
        self._log(logging.INFO, status, message)

    def error(self, status: str, message: str, exc_info: Any = None) -> None:
        self._log(logging.ERROR, status, message, exc_info)
