"""Pruebas HTTP de `GET /telemetry/report` (plan de telemetría, sección 16.3), sobre SQLite."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event as sa_event
from sqlmodel import Session

from app.core.cache import TTLCache
from app.domains.telemetry import report
from app.domains.telemetry.models import TELEMETRY_METADATA, TelemetryEventRow
from app.domains.users.models import Role

URL = "/telemetry/report"
NOW = datetime(2026, 11, 20, 10, 30, 15, tzinfo=UTC)
METRIC_KEYS = {"events_per_day", "error_rate_by_type", "api_latency_by_route", "auth_failure_rate"}

pytestmark = pytest.mark.integration


class Clock:
    """Reloj controlable para el TTL de la cache (monotónico, en segundos)."""

    def __init__(self) -> None:
        self.seconds = 1000.0

    def __call__(self) -> float:
        return self.seconds


@pytest.fixture(autouse=True)
def telemetry_table(inventory_engine):
    TELEMETRY_METADATA.create_all(inventory_engine)
    return inventory_engine


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    """Fija "ahora" para que el período por defecto sea predecible."""
    current = {"now": NOW}
    monkeypatch.setattr(report, "utc_now", lambda: current["now"])
    return current


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    """Una cache nueva con un reloj controlable en cada prueba."""
    fake = Clock()
    monkeypatch.setattr(report, "report_cache", TTLCache(report.CACHE_TTL_SECONDS, clock=fake))
    return fake


@pytest.fixture
def admin_headers(make_user):
    _, headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    return headers


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


@pytest.fixture
def selects(telemetry_table):
    """Las consultas SELECT a telemetry_events que se ejecutan durante la prueba."""
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        if "telemetry_events" in statement and statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    sa_event.listen(telemetry_table, "before_cursor_execute", capture)
    yield statements
    sa_event.remove(telemetry_table, "before_cursor_execute", capture)


# --- Acceso -----------------------------------------------------------------------------------------------


def test_without_token_is_401(api):
    assert api.get(URL).status_code == 401


def test_a_user_who_is_not_admin_gets_403(api, auth_headers):
    response = api.get(URL, headers=auth_headers)

    assert response.status_code == 403


def test_authentication_is_checked_before_the_dates(api):
    assert api.get(URL, params={"start_date": "ayer"}).status_code == 401


# --- Respuesta --------------------------------------------------------------------------------------------


def test_without_parameters_reports_the_last_7_days_with_the_four_metrics(api, admin_headers, store):
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

    response = api.get(URL, headers=admin_headers)

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    body = response.json()
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
    assert body["metrics"]["auth_failure_rate"] == [
        {"date": "2026-11-19", "attempts": 2, "failed": 1, "failure_rate": 0.5}
    ]


def test_explicit_dates_set_the_period(api, admin_headers, store):
    store("page_viewed", datetime(2026, 11, 2, 9, tzinfo=UTC), route="/inventario")

    response = api.get(URL, headers=admin_headers, params={"start_date": "2026-11-01", "end_date": "2026-11-03"})

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == {"from": "2026-11-01T00:00:00Z", "to": "2026-11-03T00:00:00Z"}
    assert [item["total"] for item in body["metrics"]["events_per_day"]] == [0, 1]


def test_an_empty_table_still_answers_with_the_structure(api, admin_headers):
    body = api.get(URL, headers=admin_headers).json()

    assert set(body["metrics"]) == METRIC_KEYS
    assert all(item["total"] == 0 for item in body["metrics"]["events_per_day"])
    assert body["metrics"]["error_rate_by_type"] == []


# --- Cache ------------------------------------------------------------------------------------------------


def test_a_repeated_request_within_the_ttl_is_served_from_the_cache_without_querying(
    api, admin_headers, store, selects
):
    store("page_viewed", NOW - timedelta(hours=1), route="/inventario")

    first = api.get(URL, headers=admin_headers)
    queries_after_first = len(selects)
    second = api.get(URL, headers=admin_headers)

    assert (first.headers["X-Cache"], second.headers["X-Cache"]) == ("MISS", "HIT")
    assert queries_after_first == 4
    assert len(selects) == 4
    assert second.json() == first.json()


def test_without_parameters_the_cached_period_is_kept_within_the_ttl(api, admin_headers, frozen_now, clock):
    first = api.get(URL, headers=admin_headers).json()

    frozen_now["now"] = NOW + timedelta(seconds=30)
    clock.seconds += 30
    second = api.get(URL, headers=admin_headers)

    assert second.headers["X-Cache"] == "HIT"
    assert second.json()["period"] == first["period"]


def test_after_the_ttl_the_report_is_recalculated(api, admin_headers, store, frozen_now, clock):
    api.get(URL, headers=admin_headers)
    store("page_viewed", NOW - timedelta(minutes=5), route="/inventario")

    clock.seconds += 59
    within = api.get(URL, headers=admin_headers)
    frozen_now["now"] = NOW + timedelta(seconds=61)
    clock.seconds += 2
    after = api.get(URL, headers=admin_headers)

    assert within.headers["X-Cache"] == "HIT"
    assert sum(item["total"] for item in within.json()["metrics"]["events_per_day"]) == 0
    assert after.headers["X-Cache"] == "MISS"
    assert sum(item["total"] for item in after.json()["metrics"]["events_per_day"]) == 1
    assert after.json()["period"]["to"] == "2026-11-20T10:31:16Z"


def test_each_combination_of_dates_has_its_own_cache_entry(api, admin_headers):
    default = api.get(URL, headers=admin_headers)
    explicit = api.get(URL, headers=admin_headers, params={"start_date": "2026-11-01"})
    same_date_other_spelling = api.get(URL, headers=admin_headers, params={"start_date": "2026-11-01T00:00:00Z"})

    assert [r.headers["X-Cache"] for r in (default, explicit, same_date_other_spelling)] == ["MISS", "MISS", "HIT"]


# --- Errores ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"start_date": "ayer"}, "invalid_date"),
        ({"end_date": "2026-02-30"}, "invalid_date"),
        ({"start_date": "2026-11-10", "end_date": "2026-11-10"}, "invalid_period"),
        ({"start_date": "2026-11-21"}, "invalid_period"),
        ({"start_date": "2026-01-01", "end_date": "2026-11-01"}, "period_too_long"),
    ],
)
def test_bad_dates_are_422_with_their_code(api, admin_headers, params, code):
    response = api.get(URL, headers=admin_headers, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_a_database_failure_is_503_is_logged_and_is_not_cached(api, admin_headers, telemetry_table, caplog):
    TELEMETRY_METADATA.drop_all(telemetry_table)
    caplog.set_level(logging.INFO, logger="api.telemetry")

    failed = api.get(URL, headers=admin_headers)

    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "telemetry_report_unavailable"
    lines = [record.getMessage() for record in caplog.records if record.name == "api.telemetry"]
    assert any("002_telemetry_events.sql" in line for line in lines)

    TELEMETRY_METADATA.create_all(telemetry_table)
    recovered = api.get(URL, headers=admin_headers)

    assert recovered.status_code == 200
    assert recovered.headers["X-Cache"] == "MISS"


# --- Contrato ---------------------------------------------------------------------------------------------


def test_openapi_documents_the_query_parameters_and_the_response_model(api):
    operation = api.get("/openapi.json").json()["paths"][URL]["get"]

    assert {parameter["name"] for parameter in operation["parameters"]} == {"start_date", "end_date"}
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/TelemetryReport"
    }
