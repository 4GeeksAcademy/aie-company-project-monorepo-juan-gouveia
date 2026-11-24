"""Pruebas de `job_runner`: consultas, transiciones, lock, idempotencia, fallos y abandonadas."""

import logging
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

import pytest
from brasaland_jobs import job_runner
from brasaland_jobs.job_runner import JobOutcome, LockHeld
from brasaland_jobs.logs import LOGGER_NAME, configure_logging, formatter
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

JOB = "nightly_export"
DAY = date(2026, 11, 24)


def runs(engine, job_name=JOB, target_date=None):
    with engine.connect() as conn:
        return job_runner.list_runs(conn, job_name, target_date)


def add_run(engine, clock, *, status, target_date=DAY, job_name=JOB, error_message=None):
    """Inserta una fila en el estado pedido, con los datos que exige ese estado."""
    now = clock()
    values = {"job_name": job_name, "target_date": target_date, "status": status, "created_at": now}
    if status != "pending":
        values["started_at"] = now
    if status in ("completed", "failed"):
        values["finished_at"] = now
    if status == "failed":
        values["error_message"] = error_message or "boom"
    with engine.begin() as conn:
        conn.execute(insert(job_runner.job_runs).values(**values))


# --- Consultas ------------------------------------------------------------------------------------


def test_has_processing_lock_only_sees_processing_rows_of_the_same_job(engine, clock):
    with engine.connect() as conn:
        assert not job_runner.has_processing_lock(conn, JOB)
    add_run(engine, clock, status="pending")
    add_run(engine, clock, status="completed")
    add_run(engine, clock, status="processing", job_name="otro_job")
    with engine.connect() as conn:
        assert not job_runner.has_processing_lock(conn, JOB)
    add_run(engine, clock, status="processing", target_date=date(2026, 11, 1))
    with engine.connect() as conn:
        assert job_runner.has_processing_lock(conn, JOB)  # el lock es del job, no de la fecha


def test_has_completed_for_date_needs_job_date_and_status(engine, clock):
    add_run(engine, clock, status="failed")
    add_run(engine, clock, status="completed", target_date=date(2026, 11, 23))
    add_run(engine, clock, status="completed", job_name="otro_job")
    with engine.connect() as conn:
        assert not job_runner.has_completed_for_date(conn, JOB, DAY)
    add_run(engine, clock, status="completed")
    with engine.connect() as conn:
        assert job_runner.has_completed_for_date(conn, JOB, DAY)


# --- Transiciones ---------------------------------------------------------------------------------


def test_full_lifecycle_pending_processing_completed(engine, clock):
    with engine.begin() as conn:
        run_id = job_runner.create_run(conn, JOB, DAY, now=clock())
        row = job_runner.get_run(conn, run_id)
    assert row["status"] == "pending" and row["started_at"] is None and row["created_at"] is not None
    with engine.begin() as conn:
        job_runner.start_run(conn, run_id, now=clock())
        assert job_runner.get_run(conn, run_id)["status"] == "processing"
        job_runner.complete_run(conn, run_id, now=clock())
        row = job_runner.get_run(conn, run_id)
    assert row["status"] == "completed"
    assert row["started_at"] < row["finished_at"]
    assert row["error_message"] is None


def test_start_run_raises_lock_held_when_another_row_is_processing(engine, clock):
    add_run(engine, clock, status="processing", target_date=date(2026, 11, 23))
    with engine.begin() as conn:
        run_id = job_runner.create_run(conn, JOB, DAY, now=clock())
    with pytest.raises(LockHeld), engine.begin() as conn:
        job_runner.start_run(conn, run_id, now=clock())
    with engine.connect() as conn:
        assert job_runner.get_run(conn, run_id)["status"] == "pending"


def test_lock_is_released_when_the_run_closes(engine, clock):
    with engine.begin() as conn:
        first = job_runner.create_run(conn, JOB, DAY, now=clock())
        job_runner.start_run(conn, first, now=clock())
        second = job_runner.create_run(conn, JOB, date(2026, 11, 25), now=clock())
    with engine.begin() as conn:
        job_runner.fail_run(conn, first, "boom", now=clock())
        job_runner.start_run(conn, second, now=clock())  # ya no hay lock
        assert job_runner.get_run(conn, second)["status"] == "processing"


def test_transitions_require_the_previous_status(engine, clock):
    with engine.begin() as conn:
        run_id = job_runner.create_run(conn, JOB, DAY, now=clock())
    with pytest.raises(job_runner.JobRunNotOpen), engine.begin() as conn:
        job_runner.complete_run(conn, run_id, now=clock())  # pending → completed no existe
    with engine.begin() as conn:
        job_runner.start_run(conn, run_id, now=clock())
        job_runner.complete_run(conn, run_id, now=clock())
    with pytest.raises(job_runner.JobRunNotOpen), engine.begin() as conn:
        job_runner.start_run(conn, run_id, now=clock())
    with engine.begin() as conn:
        assert job_runner.fail_run(conn, run_id, "tarde", now=clock()) is False  # ya cerrada
        assert job_runner.get_run(conn, run_id)["status"] == "completed"


def test_table_rejects_statuses_outside_the_ticket(engine, clock):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            insert(job_runner.job_runs).values(job_name=JOB, target_date=DAY, status="skipped", created_at=clock())
        )


def test_failed_message_is_truncated(engine, clock):
    with engine.begin() as conn:
        run_id = job_runner.create_run(conn, JOB, DAY, now=clock())
        job_runner.fail_run(conn, run_id, "x" * 5000, now=clock())
        message = job_runner.get_run(conn, run_id)["error_message"]
    assert len(message) == job_runner.ERROR_MESSAGE_MAX_LENGTH and message.endswith("…")


def test_error_message_of_includes_the_type():
    assert job_runner.error_message_of(ValueError("CSV vacío")) == "ValueError: CSV vacío"
    assert job_runner.error_message_of(KeyboardInterrupt()) == "KeyboardInterrupt"


# --- Abandonadas (N11) ----------------------------------------------------------------------------


def test_abandon_stale_runs_closes_only_old_open_rows_of_the_job(engine, clock):
    add_run(engine, clock, status="processing", target_date=date(2026, 11, 22))
    add_run(engine, clock, status="pending", target_date=date(2026, 11, 23))
    add_run(engine, clock, status="processing", job_name="otro_job")
    add_run(engine, clock, status="completed", target_date=date(2026, 11, 21))
    clock.advance(minutes=121)
    add_run(engine, clock, status="pending")  # reciente
    with engine.begin() as conn:
        closed = job_runner.abandon_stale_runs(conn, JOB, now=clock(), stale_minutes=120)
    assert sorted(row["target_date"] for row in closed) == [date(2026, 11, 22), date(2026, 11, 23)]
    by_date = {row["target_date"]: row for row in runs(engine)}
    assert by_date[date(2026, 11, 22)]["status"] == "failed"
    assert by_date[date(2026, 11, 22)]["error_message"].startswith("abandoned: seguía en processing")
    assert by_date[date(2026, 11, 23)]["error_message"].startswith("abandoned: seguía en pending")
    assert by_date[date(2026, 11, 21)]["status"] == "completed"
    assert by_date[DAY]["status"] == "pending"
    assert runs(engine, "otro_job")[0]["status"] == "processing"


def test_abandon_stale_runs_keeps_recent_processing_rows(engine, clock):
    add_run(engine, clock, status="processing")
    clock.advance(minutes=119)
    with engine.begin() as conn:
        assert job_runner.abandon_stale_runs(conn, JOB, now=clock(), stale_minutes=120) == []
    assert runs(engine)[0]["status"] == "processing"


# --- run_job --------------------------------------------------------------------------------------


class Work:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def __call__(self):
        self.calls += 1
        if self.error is not None:
            raise self.error


def test_run_job_completes_and_calls_work_once(engine, clock, caplog):
    work = Work()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        outcome = job_runner.run_job(engine, JOB, DAY, work, clock=clock)
    assert outcome is JobOutcome.COMPLETED
    assert work.calls == 1
    [row] = runs(engine)
    assert row["status"] == "completed" and row["target_date"] == DAY
    assert [r.status for r in caplog.records] == ["pending", "processing", "completed"]
    assert all(r.job == JOB and r.levelno == logging.INFO for r in caplog.records)


def test_run_job_twice_on_the_same_day_is_the_same_as_once(engine, clock, caplog):
    work = Work()
    job_runner.run_job(engine, JOB, DAY, work, clock=clock)
    before = runs(engine)
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        outcome = job_runner.run_job(engine, JOB, DAY, work, clock=clock)
    assert outcome is JobOutcome.SKIPPED_DUPLICATE
    assert work.calls == 1
    assert runs(engine) == before  # ninguna fila nueva (N10)
    [record] = caplog.records
    assert record.status == "skipped" and "duplicado" in record.getMessage()


def test_run_job_runs_again_for_another_date(engine, clock):
    work = Work()
    job_runner.run_job(engine, JOB, DAY, work, clock=clock)
    assert job_runner.run_job(engine, JOB, date(2026, 11, 25), work, clock=clock) is JobOutcome.COMPLETED
    assert work.calls == 2


def test_run_job_retries_a_date_whose_previous_run_failed(engine, clock):
    with pytest.raises(ValueError):
        job_runner.run_job(engine, JOB, DAY, Work(ValueError("boom")), clock=clock)
    work = Work()
    assert job_runner.run_job(engine, JOB, DAY, work, clock=clock) is JobOutcome.COMPLETED
    assert [row["status"] for row in runs(engine)] == ["failed", "completed"]


def test_run_job_cancels_silently_when_another_instance_holds_the_lock(engine, clock, caplog):
    add_run(engine, clock, status="processing", target_date=date(2026, 11, 23))
    work = Work()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        outcome = job_runner.run_job(engine, JOB, DAY, work, clock=clock)
    assert outcome is JobOutcome.CANCELLED_LOCK
    assert work.calls == 0
    assert len(runs(engine)) == 1  # sin fila nueva (N10)
    [record] = caplog.records
    assert record.status == "cancelled" and record.levelno == logging.INFO


def test_run_job_that_loses_the_race_closes_its_own_row(engine, clock, monkeypatch):
    # Las dos instancias pasan la comprobación previa a la vez: el índice decide (N9).
    add_run(engine, clock, status="processing", target_date=date(2026, 11, 23))
    monkeypatch.setattr(job_runner, "has_processing_lock", lambda conn, job_name: False)
    work = Work()
    assert job_runner.run_job(engine, JOB, DAY, work, clock=clock) is JobOutcome.CANCELLED_LOCK
    assert work.calls == 0
    loser = runs(engine, target_date=DAY)[0]
    assert loser["status"] == "failed"
    assert loser["error_message"].startswith("lock_held:")
    assert loser["started_at"] is None
    with engine.connect() as conn:
        processing = conn.execute(select(job_runner.job_runs).where(job_runner.job_runs.c.status == "processing")).all()
    assert len(processing) == 1  # nunca dos


def test_run_job_marks_failed_logs_and_propagates_the_error(engine, clock, caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME), pytest.raises(RuntimeError, match="pipeline caído"):
        job_runner.run_job(engine, JOB, DAY, Work(RuntimeError("pipeline caído")), clock=clock)
    [row] = runs(engine)
    assert row["status"] == "failed"
    assert row["error_message"] == "RuntimeError: pipeline caído"
    assert row["finished_at"] >= row["started_at"]
    last = caplog.records[-1]
    assert last.levelno == logging.ERROR and last.status == "failed" and last.exc_info is not None


@pytest.mark.parametrize("interruption", [KeyboardInterrupt(), SystemExit(143)])
def test_run_job_marks_failed_on_interruptions(engine, clock, interruption):
    # SIGTERM llega como SystemExit (lo instala el script): también pasa por el finally.
    with pytest.raises(type(interruption)):
        job_runner.run_job(engine, JOB, DAY, Work(interruption), clock=clock)
    [row] = runs(engine)
    assert row["status"] == "failed"
    assert row["error_message"] in ("KeyboardInterrupt", "SystemExit: 143")


def test_run_job_marks_failed_when_completing_fails(engine, clock, monkeypatch):
    def broken_complete(conn, run_id, *, now):
        raise OSError("conexión perdida")

    monkeypatch.setattr(job_runner, "complete_run", broken_complete)
    with pytest.raises(OSError):
        job_runner.run_job(engine, JOB, DAY, Work(), clock=clock)
    [row] = runs(engine)
    assert row["status"] == "failed" and row["error_message"] == "OSError: conexión perdida"


def test_run_job_never_leaves_processing_after_an_exception(engine, clock):
    for error in (ValueError("a"), MemoryError(), KeyboardInterrupt()):
        with pytest.raises(type(error)):
            job_runner.run_job(engine, JOB, DAY, Work(error), clock=clock)
    with engine.connect() as conn:
        assert not job_runner.has_processing_lock(conn, JOB)
    assert {row["status"] for row in runs(engine)} == {"failed"}


def test_run_job_logs_when_it_cannot_mark_failed_and_keeps_the_original_error(engine, clock, monkeypatch, caplog):
    def broken_fail(conn, run_id, message, *, now):
        raise OSError("base caída")

    monkeypatch.setattr(job_runner, "fail_run", broken_fail)
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME), pytest.raises(ValueError, match="original"):
        job_runner.run_job(engine, JOB, DAY, Work(ValueError("original")), clock=clock)
    last = caplog.records[-1]
    assert last.levelno == logging.ERROR and last.status == "processing"
    assert "abandoned" in last.getMessage() and "ValueError: original" in last.getMessage()


def test_run_job_closes_abandoned_runs_before_checking_the_lock(engine, clock, caplog):
    add_run(engine, clock, status="processing", target_date=date(2026, 11, 23))  # proceso muerto
    clock.advance(minutes=121)
    work = Work()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        assert job_runner.run_job(engine, JOB, DAY, work, clock=clock) is JobOutcome.COMPLETED
    assert work.calls == 1
    statuses = {row["target_date"]: row["status"] for row in runs(engine)}
    assert statuses == {date(2026, 11, 23): "failed", DAY: "completed"}
    first = caplog.records[0]
    assert first.levelno == logging.ERROR and first.status == "failed" and "abandoned" in first.getMessage()


def test_run_job_honours_the_stale_threshold(engine, clock):
    add_run(engine, clock, status="processing", target_date=date(2026, 11, 23))
    clock.advance(minutes=30)
    assert job_runner.run_job(engine, JOB, DAY, Work(), clock=clock, stale_minutes=120) is JobOutcome.CANCELLED_LOCK
    assert job_runner.run_job(engine, JOB, DAY, Work(), clock=clock, stale_minutes=20) is JobOutcome.COMPLETED


def test_processing_row_without_started_at_is_rejected(engine, clock):
    with engine.begin() as conn:
        run_id = job_runner.create_run(conn, JOB, DAY, now=clock())
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(update(job_runner.job_runs).where(job_runner.job_runs.c.id == run_id).values(status="processing"))


# --- Logs -----------------------------------------------------------------------------------------


def test_log_line_has_utc_timestamp_job_and_status():
    record = logging.LogRecord(LOGGER_NAME, logging.INFO, __file__, 1, "target_date=2026-11-24 | Fin", None, None)
    record.job, record.status, record.created = JOB, "completed", 1764057600.0  # 2025-11-25T08:00:00Z
    assert formatter().format(record) == "2025-11-25T08:00:00Z | INFO | nightly_export | completed | target_date=2026-11-24 | Fin"


def test_configure_logging_is_idempotent_and_tolerates_records_without_job():
    logger = configure_logging()
    configure_logging()
    handlers = [h for h in logger.handlers if getattr(h, "_brasaland_jobs", False)]
    try:
        assert len(handlers) == 1
        record = logging.LogRecord(LOGGER_NAME, logging.INFO, __file__, 1, "sin job", None, None)
        assert handlers[0].filter(record) and " | - | - | sin job" in handlers[0].format(record)
    finally:
        # Deja el logger como estaba: caplog necesita que propague a la raíz.
        for handler in handlers:
            logger.removeHandler(handler)
        logger.propagate = True


# --- Independencia de la API (criterio 1) ---------------------------------------------------------


def test_package_does_not_depend_on_fastapi():
    pyproject = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert not any("fastapi" in dep.lower() for dep in pyproject["project"]["dependencies"])
    code = "import sys, brasaland_jobs.job_runner, brasaland_jobs.logs; print('fastapi' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "False"
