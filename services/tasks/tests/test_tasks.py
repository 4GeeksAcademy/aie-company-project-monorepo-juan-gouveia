"""Tareas del worker sin Redis ni Supabase: Celery en modo eager y la DLQ en SQLite.

En modo eager, los reintentos se ejecutan en el momento (Celery ignora el countdown) y `on_failure` publica
en la cola dead_letter ejecutando `dead_letters.record` también en el momento. Las esperas se comprueban en
el log, que registra el countdown de cada reintento. El informe se sustituye por una función falsa: las
métricas de `analysis.py` se prueban en la API.
"""

from __future__ import annotations

import json
import logging

import pytest
from brasaland_tasks import tasks
from brasaland_tasks.celery_app import VISIBILITY_TIMEOUT_SECONDS, app
from brasaland_tasks.dead_letters import build_entry
from brasaland_tasks.errors import InjectedTransientFault, is_transient
from brasaland_tasks.faults import InvalidFaultInjection, parse_fault_injection
from brasaland_tasks.logs import LOGGER_NAME
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.pool import StaticPool

PERIOD = {"start": "2026-11-18T00:00:00+00:00", "end": "2026-11-25T00:00:00+00:00", "requested_by": "user-42"}
REPORT = {"period": {"from": "2026-11-18T00:00:00Z", "to": "2026-11-25T00:00:00Z"}, "metrics": {}}

DLQ_TABLE = """
CREATE TABLE ops.task_dead_letters (
    id INTEGER PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,
    task_name TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    reason TEXT NOT NULL,
    error_message TEXT NOT NULL,
    traceback TEXT,
    task_args TEXT NOT NULL,
    failed_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


class Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def states(self, task_name: str) -> list[str]:
        return [r.state for r in self.records if r.task_name == task_name]


@pytest.fixture(autouse=True)
def eager(monkeypatch):
    monkeypatch.setitem(app.conf, "task_always_eager", True)
    monkeypatch.setitem(app.conf, "task_eager_propagates", False)
    monkeypatch.delenv("TASKS_FAULT_INJECTION", raising=False)


@pytest.fixture
def logs():
    handler = Records()
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


@pytest.fixture
def engine(monkeypatch):
    """SQLite en memoria con un esquema `ops` adjunto, como ops.task_dead_letters en Supabase."""
    db = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(db, "connect")
    def attach_ops(dbapi_connection, _record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS ops")

    with db.begin() as connection:
        connection.exec_driver_sql(DLQ_TABLE)
    monkeypatch.setattr(tasks, "get_engine", lambda: db)
    return db


@pytest.fixture
def report(monkeypatch):
    """Sustituye el cálculo del informe. `outcomes` es una cola: excepción a lanzar o None (éxito)."""
    calls: list[tuple] = []
    outcomes: list[BaseException | None] = []

    def fake_build_report(connection, start, end):
        calls.append((start, end))
        outcome = outcomes.pop(0) if outcomes else None
        if outcome is not None:
            raise outcome
        return REPORT

    monkeypatch.setattr(tasks, "build_report", fake_build_report)
    return calls, outcomes


def dead_letters(engine) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT * FROM ops.task_dead_letters ORDER BY id")).mappings().all()
    return [dict(row) for row in rows]


def operational_error() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("server closed the connection unexpectedly"))


def run_report():
    return tasks.telemetry_report.apply(kwargs=PERIOD)


# --- Registro y esperas ---------------------------------------------------------------------------------


def test_tasks_are_registered_by_the_names_the_api_uses():
    # `tasks.telemetry_report` es un proxy de Celery: se compara con ==, no con `is`.
    assert app.tasks["telemetry.report"] == tasks.telemetry_report
    assert app.tasks["dead_letters.record"] == tasks.record_dead_letter
    assert tasks.telemetry_report.max_retries == 3


def test_dead_letter_records_are_routed_to_their_queue():
    assert app.amqp.router.route({}, "dead_letters.record")["queue"].name == "dead_letter"
    assert app.amqp.router.route({}, "telemetry.report")["queue"].name == "default"


def test_retry_waits_are_10_20_and_40_seconds():
    assert [tasks.retry_countdown(n) for n in range(3)] == [10, 20, 40]


def test_dead_letter_waits_stay_below_the_visibility_timeout():
    waits = [tasks.dead_letter_countdown(n) for n in range(10)]
    assert waits[:5] == [10, 20, 40, 80, 120]
    assert max(waits) < VISIBILITY_TIMEOUT_SECONDS


# --- telemetry.report -----------------------------------------------------------------------------------


def test_report_succeeds_without_dead_letter(engine, report, logs):
    result = run_report()
    assert result.state == "SUCCESS"
    assert result.result == REPORT
    assert dead_letters(engine) == []
    assert logs.states("telemetry.report") == ["started", "success"]


def test_report_receives_the_period_in_utc(engine, report):
    calls, _ = report
    run_report()
    start, end = calls[0]
    assert start.isoformat() == "2026-11-18T00:00:00+00:00"
    assert end.isoformat() == "2026-11-25T00:00:00+00:00"


def test_transient_database_error_is_retried_then_succeeds(engine, report, logs):
    calls, outcomes = report
    outcomes.extend([operational_error(), operational_error()])
    result = run_report()
    assert result.state == "SUCCESS"
    assert len(calls) == 3
    assert dead_letters(engine) == []
    retries = [r.getMessage() for r in logs.records if r.state == "retry"]
    assert [m.split(":")[0] for m in retries] == ["Reintento en 10 s", "Reintento en 20 s"]


def test_three_failed_retries_send_the_task_to_the_dead_letter_queue(engine, report, logs):
    calls, outcomes = report
    outcomes.extend(operational_error() for _ in range(4))
    result = run_report()
    assert result.state == "FAILURE"
    assert len(calls) == 4  # 1 ejecución + 3 reintentos (max_retries=3)
    [row] = dead_letters(engine)
    assert row["task_id"] == result.id
    assert row["task_name"] == "telemetry.report"
    assert row["attempt"] == 4
    assert row["reason"] == "max_retries_exceeded"
    assert row["error_message"].startswith("OperationalError: ")
    assert "server closed the connection unexpectedly" in row["error_message"]
    assert "Traceback" in row["traceback"]
    assert json.loads(row["task_args"]) == PERIOD
    # Celery llama a on_failure (envío a la DLQ) antes de emitir la señal task_failure.
    assert logs.states("telemetry.report") == ["started", "retry"] * 3 + ["started", "dead_letter", "failure"]
    assert logs.states("dead_letters.record") == ["started", "recorded", "success"]


def test_permanent_error_goes_to_the_dead_letter_queue_without_retry(engine, report, logs):
    calls, outcomes = report
    outcomes.append(ProgrammingError("SELECT", {}, Exception('relation "telemetry_events" does not exist')))
    result = run_report()
    assert result.state == "FAILURE"
    assert len(calls) == 1
    [row] = dead_letters(engine)
    assert (row["attempt"], row["reason"]) == (1, "non_retryable")
    assert "telemetry_events" in row["error_message"]
    assert "retry" not in logs.states("telemetry.report")


def test_soft_time_limit_is_retried(engine, report):
    calls, outcomes = report
    outcomes.append(SoftTimeLimitExceeded())
    assert run_report().state == "SUCCESS"
    assert len(calls) == 2


def test_invalid_period_is_permanent(engine, report):
    calls, _ = report
    result = tasks.telemetry_report.apply(kwargs={**PERIOD, "start": "ayer"})
    assert result.state == "FAILURE"
    assert calls == []
    [row] = dead_letters(engine)
    assert row["reason"] == "non_retryable"
    assert row["error_message"].startswith("InvalidReportPeriod: ")


def test_dead_letter_keeps_only_reference_arguments(engine, report):
    _, outcomes = report
    outcomes.append(ValueError("boom"))
    tasks.telemetry_report.apply(kwargs=PERIOD)
    [row] = dead_letters(engine)
    assert set(json.loads(row["task_args"])) == {"start", "end", "requested_by"}
    assert "metrics" not in row["traceback"]


def test_log_never_contains_task_arguments(engine, report, logs):
    _, outcomes = report
    outcomes.append(operational_error())
    run_report()
    text_logged = "\n".join(r.getMessage() + r.refs for r in logs.records)
    assert "user-42" not in text_logged
    assert "2026-11-18" not in text_logged


def test_each_log_line_carries_task_id_attempt_and_duration(engine, report, logs):
    _, outcomes = report
    outcomes.append(operational_error())
    result = run_report()
    lines = [r for r in logs.records if r.task_name == "telemetry.report"]
    assert all(f"task_id={result.id}" in r.refs for r in lines)
    assert [r.refs.split()[1] for r in lines] == ["attempt=1", "attempt=1", "attempt=2", "attempt=2"]
    assert all("duration_ms=" in r.refs for r in lines if r.state in {"retry", "success"})


def test_failure_log_has_the_full_error_and_traceback(engine, report, logs):
    _, outcomes = report
    outcomes.append(ValueError("dato inesperado"))
    run_report()
    [failure] = [r for r in logs.records if r.state == "failure"]
    assert failure.levelno == logging.ERROR
    assert "ValueError: dato inesperado" in failure.getMessage()
    assert "Traceback" in failure.getMessage()


def test_failure_is_logged_when_the_dead_letter_queue_cannot_be_reached(engine, report, logs, monkeypatch):
    _, outcomes = report
    outcomes.append(ValueError("boom"))

    def broker_down(*args, **kwargs):
        raise ConnectionError("Redis no responde")

    monkeypatch.setattr(tasks.record_dead_letter, "apply_async", broker_down)
    result = run_report()
    assert result.state == "FAILURE"
    [critical] = [r for r in logs.records if r.levelno == logging.CRITICAL]
    assert "Redis no responde" in critical.getMessage()
    assert "ValueError: boom" in critical.getMessage()


# --- Inyección de fallos (T12) --------------------------------------------------------------------------


def test_injected_transient_fault_exhausts_retries(engine, report, monkeypatch):
    calls, _ = report
    monkeypatch.setenv("TASKS_FAULT_INJECTION", "transient")
    result = run_report()
    assert result.state == "FAILURE"
    assert calls == []  # el fallo llega antes de tocar la base
    [row] = dead_letters(engine)
    assert (row["attempt"], row["reason"]) == (4, "max_retries_exceeded")
    assert row["error_message"].startswith("InjectedTransientFault: ")


def test_injected_transient_fault_with_count_recovers(engine, report, monkeypatch, logs):
    calls, _ = report
    monkeypatch.setenv("TASKS_FAULT_INJECTION", "transient:2")
    result = run_report()
    assert result.state == "SUCCESS"
    assert len(calls) == 1
    assert logs.states("telemetry.report") == ["started", "retry", "started", "retry", "started", "success"]


def test_injected_permanent_fault_is_not_retried(engine, report, monkeypatch):
    monkeypatch.setenv("TASKS_FAULT_INJECTION", "permanent")
    result = run_report()
    assert result.state == "FAILURE"
    [row] = dead_letters(engine)
    assert (row["attempt"], row["reason"]) == (1, "non_retryable")


@pytest.mark.parametrize("raw", ["transient:0", "transient:x", "siempre", "permanent:2"])
def test_unknown_fault_injection_values_are_rejected(raw):
    with pytest.raises(InvalidFaultInjection):
        parse_fault_injection(raw)


def test_empty_fault_injection_does_nothing():
    assert parse_fault_injection("") is None
    assert parse_fault_injection(None) is None


def test_error_classification():
    assert is_transient(operational_error())
    assert is_transient(SoftTimeLimitExceeded())
    assert is_transient(InjectedTransientFault("x"))
    assert not is_transient(ProgrammingError("SELECT", {}, Exception("syntax error")))
    assert not is_transient(ValueError("x"))


# --- dead_letters.record --------------------------------------------------------------------------------


def entry(task_id: str = "t-1") -> dict:
    return build_entry(
        task_id=task_id,
        task_name="telemetry.report",
        attempt=4,
        reason="max_retries_exceeded",
        error_message="OperationalError: timeout",
        traceback="Traceback …",
        kwargs={**PERIOD, "otro": "descartado"},
    )


def test_record_is_idempotent_by_task_id(engine, logs):
    first = tasks.record_dead_letter.apply(kwargs={"entry": entry()})
    second = tasks.record_dead_letter.apply(kwargs={"entry": entry()})
    assert first.result == {"task_id": "t-1", "inserted": True}
    assert second.result == {"task_id": "t-1", "inserted": False}
    assert len(dead_letters(engine)) == 1
    assert logs.states("dead_letters.record").count("duplicate") == 1


def test_record_drops_non_reference_arguments(engine):
    tasks.record_dead_letter.apply(kwargs={"entry": entry()})
    assert json.loads(dead_letters(engine)[0]["task_args"]) == PERIOD


def test_record_retries_while_the_database_is_down(engine, monkeypatch, logs):
    failures = [operational_error(), operational_error()]
    real_insert = tasks.insert_dead_letter

    def flaky_insert(connection, value):
        if failures:
            raise failures.pop(0)
        return real_insert(connection, value)

    monkeypatch.setattr(tasks, "insert_dead_letter", flaky_insert)
    result = tasks.record_dead_letter.apply(kwargs={"entry": entry()})
    assert result.state == "SUCCESS"
    assert len(dead_letters(engine)) == 1
    retries = [r.getMessage().split(":")[0] for r in logs.records if r.state == "retry"]
    assert retries == ["Reintento en 10 s", "Reintento en 20 s"]


def test_invalid_record_fails_without_retry(engine, logs):
    bad = {**entry(), "reason": "timeout"}
    result = tasks.record_dead_letter.apply(kwargs={"entry": bad})
    assert result.state == "FAILURE"
    assert dead_letters(engine) == []
    assert "retry" not in logs.states("dead_letters.record")
    [critical] = [r for r in logs.records if r.levelno == logging.CRITICAL]
    assert "OperationalError: timeout" in critical.getMessage()
