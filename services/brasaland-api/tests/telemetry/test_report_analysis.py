"""Pipeline de análisis de la telemetría (`services/telemetry/analysis.py`, plan de telemetría, sección 16).

Las métricas se calculan sobre una tabla `telemetry_events` en SQLite, donde `timestamp` llega como
texto: si el pipeline no lo convirtiera a datetime antes de agrupar, los días saldrían mal.
"""

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import event as sa_event
from sqlmodel import Session

from app.domains.telemetry.models import TELEMETRY_METADATA, TelemetryEventRow
from brasaland_telemetry import analysis
from brasaland_telemetry.analysis import (
    api_latency_by_route,
    auth_failure_rate,
    error_rate_by_type,
    events_per_day,
)

METRICS = [events_per_day, error_rate_by_type, api_latency_by_route, auth_failure_rate]
LEVEL_OF = {
    "page_viewed": "info",
    "api_latency_recorded": "info",
    "login_succeeded": "info",
    "login_failed": "warn",
    "api_error_returned": "warn",
    "frontend_error_captured": "error",
}
START = datetime(2026, 11, 17, tzinfo=UTC)
END = datetime(2026, 11, 20, tzinfo=UTC)


def at(day: int, hour: int = 12, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, second, tzinfo=UTC)


def row(event_type: str, when: datetime, **tags) -> TelemetryEventRow:
    return TelemetryEventRow(
        id=uuid4(), timestamp=when, service="backoffice", event_type=event_type, level=LEVEL_OF[event_type], tags=tags
    )


def latency(when: datetime, route: str, duration_ms: float, sample_rate: float = 1.0, method: str = "GET") -> TelemetryEventRow:
    return row(
        "api_latency_recorded",
        when,
        method=method,
        route=route,
        status_code=200,
        duration_ms=duration_ms,
        sample_rate=sample_rate,
    )


@pytest.fixture
def engine(inventory_engine):
    TELEMETRY_METADATA.create_all(inventory_engine)
    return inventory_engine


@pytest.fixture
def store(engine):
    def _store(*rows: TelemetryEventRow) -> None:
        with Session(engine) as session:
            session.add_all(rows)
            session.commit()

    return _store


@pytest.fixture
def run(engine):
    def _run(metric, start: datetime = START, end: datetime = END):
        with engine.connect() as connection:
            return metric(connection, start, end)

    return _run


# --- events_per_day ---------------------------------------------------------------------------------------


def test_events_per_day_counts_each_level_per_utc_day_and_fills_empty_days(store, run):
    store(
        row("page_viewed", at(17, 9)),
        row("page_viewed", at(17, 23, 59, 59)),
        row("login_failed", at(17, 10)),
        row("frontend_error_captured", at(19, 0, 0, 0)),
        row("page_viewed", at(19, 8)),
    )

    assert run(events_per_day) == [
        {"date": "2026-11-17", "total": 3, "info": 2, "warn": 1, "error": 0},
        {"date": "2026-11-18", "total": 0, "info": 0, "warn": 0, "error": 0},
        {"date": "2026-11-19", "total": 2, "info": 1, "warn": 0, "error": 1},
    ]


def test_the_window_is_start_inclusive_and_end_exclusive(store, run):
    store(
        row("page_viewed", START - timedelta(seconds=1)),
        row("page_viewed", START),
        row("page_viewed", END - timedelta(seconds=1)),
        row("page_viewed", END),
    )

    rows = run(events_per_day)

    assert [item["total"] for item in rows] == [1, 0, 1]
    assert rows[-1]["date"] == "2026-11-19"


def test_a_partial_last_day_is_still_a_row(store, run):
    store(row("page_viewed", at(20, 9)))

    rows = run(events_per_day, START, at(20, 10))

    assert rows[-1] == {"date": "2026-11-20", "total": 1, "info": 1, "warn": 0, "error": 0}


# --- error_rate_by_type -----------------------------------------------------------------------------------


def test_error_rate_by_type_divides_each_failure_type_by_the_day_volume(store, run):
    store(
        *[row("page_viewed", at(18, 9, minute)) for minute in range(6)],
        row("api_error_returned", at(18, 10), method="GET", route="/x", status_code=404, error_code="not_found"),
        row("api_error_returned", at(18, 11), method="GET", route="/x", status_code=404, error_code="not_found"),
        row("frontend_error_captured", at(18, 12)),
        row("login_failed", at(18, 13), failure_reason="invalid_credentials"),
        row("page_viewed", at(19, 9)),
        row("login_failed", at(19, 10), failure_reason="invalid_credentials"),
    )

    assert run(error_rate_by_type) == [
        {"date": "2026-11-18", "event_type": "api_error_returned", "level": "warn", "count": 2, "rate": 0.2},
        {"date": "2026-11-18", "event_type": "frontend_error_captured", "level": "error", "count": 1, "rate": 0.1},
        {"date": "2026-11-18", "event_type": "login_failed", "level": "warn", "count": 1, "rate": 0.1},
        {"date": "2026-11-19", "event_type": "login_failed", "level": "warn", "count": 1, "rate": 0.5},
    ]


def test_error_rate_by_type_rounds_to_four_decimals(store, run):
    store(row("login_failed", at(18)), row("page_viewed", at(18, 13)), row("page_viewed", at(18, 14)))

    assert run(error_rate_by_type)[0]["rate"] == 0.3333


# --- api_latency_by_route ---------------------------------------------------------------------------------


def test_latency_mean_is_weighted_by_the_inverse_of_the_sample_rate(store, run):
    store(
        # Una petición rápida muestreada 1 de cada 10 representa a 10; la lenta se guarda siempre.
        latency(at(18, 9), "/inventory/products", 100, sample_rate=0.1),
        latency(at(18, 10), "/inventory/products", 1000, sample_rate=1),
    )

    assert run(api_latency_by_route) == [
        {
            "date": "2026-11-18",
            "method": "GET",
            "route": "/inventory/products",
            "samples": 2,
            "avg_ms": round((100 * 10 + 1000) / 11, 1),
            "max_ms": 1000.0,
        }
    ]


def test_latency_is_grouped_by_day_method_and_route_slowest_first(store, run):
    store(
        latency(at(18, 9), "/inventory/products", 50),
        latency(at(18, 9), "/inventory/orders", 300),
        latency(at(18, 9), "/inventory/orders", 900, method="POST"),
        latency(at(19, 9), "/inventory/products", 80),
    )

    rows = run(api_latency_by_route)

    assert [(item["date"], item["method"], item["route"], item["avg_ms"]) for item in rows] == [
        ("2026-11-18", "POST", "/inventory/orders", 900.0),
        ("2026-11-18", "GET", "/inventory/orders", 300.0),
        ("2026-11-18", "GET", "/inventory/products", 50.0),
        ("2026-11-19", "GET", "/inventory/products", 80.0),
    ]


def test_latency_drops_rows_without_route_or_duration_and_treats_a_bad_sample_rate_as_one(store, run):
    store(
        row("api_latency_recorded", at(18, 9), method="GET", duration_ms=10, sample_rate=1),
        row("api_latency_recorded", at(18, 9), method="GET", route="/a", sample_rate=1),
        latency(at(18, 10), "/a", 200, sample_rate=0),
        latency(at(18, 11), "/a", 400, sample_rate=1),
        row("page_viewed", at(18, 12), route="/inventario"),
    )

    assert run(api_latency_by_route) == [
        {"date": "2026-11-18", "method": "GET", "route": "/a", "samples": 2, "avg_ms": 300.0, "max_ms": 400.0}
    ]


# --- auth_failure_rate ------------------------------------------------------------------------------------


def test_auth_failure_rate_is_failed_over_all_attempts_per_day(store, run):
    store(
        row("login_failed", at(18, 9), failure_reason="invalid_credentials"),
        row("login_succeeded", at(18, 9, 1), user_role="admin"),
        row("login_succeeded", at(18, 15), user_role="manager"),
        row("login_succeeded", at(18, 16), user_role="user"),
        row("login_failed", at(19, 9), failure_reason="network_error"),
        row("page_viewed", at(19, 10)),
    )

    assert run(auth_failure_rate) == [
        {"date": "2026-11-18", "attempts": 4, "failed": 1, "failure_rate": 0.25},
        {"date": "2026-11-19", "attempts": 1, "failed": 1, "failure_rate": 1.0},
    ]


# --- Propiedades comunes ----------------------------------------------------------------------------------


@pytest.fixture
def mixed_events(store):
    store(
        row("page_viewed", at(18, 9)),
        row("login_failed", at(18, 9), failure_reason="invalid_credentials"),
        row("login_succeeded", at(18, 9, 1), user_role="admin"),
        latency(at(18, 10), "/inventory/orders", 250, sample_rate=0.1),
        row("frontend_error_captured", at(19, 11)),
    )


@pytest.mark.parametrize("metric", METRICS, ids=lambda metric: metric.__name__)
def test_every_metric_returns_json_ready_records_with_native_types(mixed_events, run, metric):
    rows = run(metric)

    assert isinstance(rows, list) and rows
    assert all(isinstance(item, dict) and isinstance(item["date"], str) for item in rows)
    assert all(type(value) in (str, int, float) for item in rows for value in item.values())
    json.dumps(rows)


@pytest.mark.parametrize("metric", METRICS, ids=lambda metric: metric.__name__)
def test_every_metric_is_repeatable_with_the_same_parameters(mixed_events, run, metric):
    assert run(metric) == run(metric)


@pytest.mark.parametrize("metric", METRICS, ids=lambda metric: metric.__name__)
def test_an_empty_window_gives_no_rows_except_the_zero_days(engine, run, metric):
    rows = run(metric)

    if metric is events_per_day:
        assert [item["total"] for item in rows] == [0, 0, 0]
    else:
        assert rows == []


@pytest.mark.parametrize("metric", METRICS, ids=lambda metric: metric.__name__)
def test_every_metric_loads_its_rows_with_one_windowed_query(engine, mixed_events, run, metric):
    statements: list[tuple[str, object]] = []

    @sa_event.listens_for(engine, "before_cursor_execute")
    def capture(_conn, _cursor, statement, parameters, _context, _executemany):
        statements.append((" ".join(statement.split()), parameters))

    try:
        run(metric)
    finally:
        sa_event.remove(engine, "before_cursor_execute", capture)

    selects = [statement for statement, _ in statements if statement.startswith("SELECT")]
    assert len(selects) == 1
    assert "FROM telemetry_events WHERE timestamp >= ? AND timestamp < ?" in selects[0]
    assert "SELECT *" not in selects[0]


def test_the_pipeline_has_no_loops():
    """Las métricas se calculan solo con operaciones de Pandas: ni bucles, ni comprensiones, ni apply."""
    source = Path(analysis.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    loops = (ast.For, ast.AsyncFor, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

    assert [type(node).__name__ for node in ast.walk(tree) if isinstance(node, loops)] == []
    assert ".apply(" not in source and ".iterrows(" not in source and ".itertuples(" not in source


def test_the_pipeline_lives_where_the_assignment_asks():
    path = Path(analysis.__file__).resolve()

    assert path.name == "analysis.py"
    assert path.parent.name == "telemetry" and path.parent.parent.name == "services"
