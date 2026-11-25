"""Contrato del resultado de la tarea `telemetry.report` (ticket #DEV-55).

El worker (`services/tasks/report.py`) arma el informe y no depende de la API; la API documenta su forma
con `TelemetryReport`. Esta prueba ejecuta el `build_report` del worker sobre SQLite con la misma tabla y
los mismos eventos que las antiguas pruebas de `GET /telemetry/report`, y valida el resultado con el
modelo de la API: si uno de los dos cambia sin el otro, falla. El resultado pasa además por JSON, como
cuando lo guarda el backend de resultados de Redis.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from brasaland_tasks.report import build_report
from sqlmodel import Session

from app.domains.telemetry.models import TELEMETRY_METADATA, TelemetryEventRow
from app.domains.telemetry.report import DEFAULT_WINDOW
from app.domains.telemetry.schemas import TelemetryReport

NOW = datetime(2026, 11, 20, 10, 30, 15, tzinfo=UTC)
METRIC_KEYS = {"events_per_day", "error_rate_by_type", "api_latency_by_route", "auth_failure_rate"}


@pytest.fixture
def telemetry_table(inventory_engine):
    TELEMETRY_METADATA.create_all(inventory_engine)
    return inventory_engine


@pytest.fixture
def store(telemetry_table):
    def _store(event_type: str, when: datetime, level: str = "info", **tags) -> None:
        with Session(telemetry_table) as session:
            session.add(
                TelemetryEventRow(
                    id=uuid4(), timestamp=when, service="backoffice", event_type=event_type, level=level, tags=tags
                )
            )
            session.commit()

    return _store


def run_task_report(engine, start: datetime, end: datetime) -> dict:
    with engine.connect() as connection:
        report = build_report(connection, start, end)
    # El backend de resultados de Celery guarda JSON: lo que llega a GET /tasks es esto.
    return json.loads(json.dumps(report))


def test_the_task_report_matches_the_api_contract_with_the_four_metrics(telemetry_table, store):
    store("page_viewed", NOW - timedelta(days=1), route="/inventario")
    store("login_failed", NOW - timedelta(days=1), level="warn", failure_reason="invalid_credentials")
    store("login_succeeded", NOW - timedelta(days=1, minutes=-1), user_role="admin")
    store(
        "api_latency_recorded",
        NOW - timedelta(hours=2),
        method="GET",
        route="/api/v1/inventory/orders",
        status_code=200,
        duration_ms=420.5,
        sample_rate=1,
    )
    store("page_viewed", NOW - timedelta(days=8), route="/fuera-de-la-ventana")

    body = run_task_report(telemetry_table, NOW - DEFAULT_WINDOW, NOW)

    TelemetryReport.model_validate(body)
    assert body["period"] == {"from": "2026-11-13T10:30:15Z", "to": "2026-11-20T10:30:15Z"}
    assert set(body["metrics"]) == METRIC_KEYS
    events = body["metrics"]["events_per_day"]
    assert [item["date"] for item in events] == [f"2026-11-{day}" for day in range(13, 21)]
    assert sum(item["total"] for item in events) == 4
    assert {"date": "2026-11-19", "total": 3, "info": 2, "warn": 1, "error": 0} in events
    assert body["metrics"]["error_rate_by_type"] == [
        {"date": "2026-11-19", "event_type": "login_failed", "level": "warn", "count": 1, "rate": 0.3333}
    ]
    assert body["metrics"]["api_latency_by_route"] == [
        {
            "date": "2026-11-20",
            "method": "GET",
            "route": "/api/v1/inventory/orders",
            "samples": 1,
            "avg_ms": 420.5,
            "max_ms": 420.5,
        }
    ]
    assert body["metrics"]["auth_failure_rate"] == [{"date": "2026-11-19", "attempts": 2, "failed": 1, "failure_rate": 0.5}]


def test_explicit_dates_set_the_period(telemetry_table, store):
    store("page_viewed", datetime(2026, 11, 2, 9, tzinfo=UTC), route="/inventario")

    body = run_task_report(telemetry_table, datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 3, tzinfo=UTC))

    TelemetryReport.model_validate(body)
    assert body["period"] == {"from": "2026-11-01T00:00:00Z", "to": "2026-11-03T00:00:00Z"}
    assert [item["total"] for item in body["metrics"]["events_per_day"]] == [0, 1]


def test_an_empty_table_still_answers_with_the_structure(telemetry_table):
    body = run_task_report(telemetry_table, NOW - DEFAULT_WINDOW, NOW)

    TelemetryReport.model_validate(body)
    assert all(item["total"] == 0 for item in body["metrics"]["events_per_day"])
    assert body["metrics"]["error_rate_by_type"] == []
