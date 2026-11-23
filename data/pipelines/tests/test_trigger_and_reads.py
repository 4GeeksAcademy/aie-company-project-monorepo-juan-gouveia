"""Disparo manual (trigger.py) y lecturas de reporting.* que usan los endpoints de services/reporting."""

import json
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pandas as pd
import pytest
from brasaland_pipelines import repository, trigger
from sqlalchemy import insert

TODAY = date(2026, 11, 25)
WEEK = date(2026, 11, 16)


@pytest.fixture
def prefect_calls(monkeypatch):
    """Prefect configurado y `create_flow_run` simulado: guarda los parámetros y devuelve un id."""
    calls = []
    flow_run_id = uuid4()

    def fake_create_flow_run(parameters):
        calls.append(parameters)
        return flow_run_id

    monkeypatch.setenv("PREFECT_API_URL", "http://prefect-server:4200/api")
    monkeypatch.setattr(trigger, "create_flow_run", fake_create_flow_run)
    return SimpleNamespace(calls=calls, flow_run_id=flow_run_id)


def test_registers_a_pending_run_and_queues_it_in_prefect(database, prefect_calls):
    run = trigger.trigger_pipeline_run(database, today=TODAY)

    assert run["status"] == "pending"
    assert run["trigger"] == "manual"
    assert (run["week_from"], run["week_to"]) == (date(2026, 10, 26), WEEK)
    assert run["prefect_flow_run_id"] == prefect_calls.flow_run_id
    assert prefect_calls.calls == [
        {"week_from": "2026-10-26", "week_to": "2026-11-16", "trigger": "manual", "run_id": str(run["id"])}
    ]


def test_a_backfill_range_and_the_requesting_user_are_recorded(database, prefect_calls):
    user = uuid4()

    run = trigger.trigger_pipeline_run(database, week_from=date(2026, 9, 7), week_to=date(2026, 9, 21), requested_by=user, today=TODAY)

    assert (run["week_from"], run["week_to"], run["requested_by"]) == (date(2026, 9, 7), date(2026, 9, 21), user)


def test_an_invalid_range_writes_nothing(database, prefect_calls):
    with pytest.raises(trigger.InvalidWeekRange, match="en curso"):
        trigger.trigger_pipeline_run(database, week_from=date(2026, 11, 23), week_to=date(2026, 11, 23), today=TODAY)

    with database.connect() as conn:
        assert repository.read_latest_pipeline_run(conn) is None
    assert prefect_calls.calls == []


def test_a_second_active_run_is_refused(database, prefect_calls):
    trigger.trigger_pipeline_run(database, today=TODAY)

    with pytest.raises(repository.PipelineRunInProgress):
        trigger.trigger_pipeline_run(database, today=TODAY)

    assert len(prefect_calls.calls) == 1


def test_without_prefect_configured_nothing_is_written(database, monkeypatch):
    monkeypatch.delenv("PREFECT_API_URL", raising=False)

    with pytest.raises(trigger.OrchestratorUnavailable):
        trigger.trigger_pipeline_run(database, today=TODAY)

    with database.connect() as conn:
        assert repository.read_latest_pipeline_run(conn) is None


def test_if_prefect_refuses_the_run_is_closed_as_failed(database, monkeypatch):
    def unreachable(parameters):
        raise trigger.OrchestratorUnavailable("Prefect no respondió: ConnectError.")

    monkeypatch.setenv("PREFECT_API_URL", "http://prefect-server:4200/api")
    monkeypatch.setattr(trigger, "create_flow_run", unreachable)

    with pytest.raises(trigger.OrchestratorUnavailable):
        trigger.trigger_pipeline_run(database, today=TODAY)

    with database.connect() as conn:
        run = repository.read_latest_pipeline_run(conn)
    assert (run["status"], run["error_message"]) == ("failed", "orchestrator_unavailable: Prefect no respondió: ConnectError.")


# --- create_flow_run: las dos llamadas a la API REST de Prefect ----------------------------------


def prefect_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_creates_the_flow_run_of_the_deployment_by_name(monkeypatch):
    monkeypatch.setenv("PREFECT_API_URL", "http://prefect-server:4200/api/")
    deployment_id, flow_run_id = uuid4(), uuid4()
    requests = []

    def handler(request):
        requests.append((request.method, request.url.path, request.content))
        if request.method == "GET":
            return httpx.Response(200, json={"id": str(deployment_id)})
        return httpx.Response(201, json={"id": str(flow_run_id)})

    assert trigger.create_flow_run({"trigger": "manual"}, client=prefect_client(handler)) == flow_run_id
    assert requests[0][:2] == ("GET", "/api/deployments/name/weekly-location-performance/weekly")
    assert requests[1][:2] == ("POST", f"/api/deployments/{deployment_id}/create_flow_run")
    assert json.loads(requests[1][2]) == {"parameters": {"trigger": "manual"}}


def test_an_unregistered_deployment_or_an_unreachable_server_is_reported(monkeypatch):
    monkeypatch.setenv("PREFECT_API_URL", "http://prefect-server:4200/api")

    with pytest.raises(trigger.OrchestratorUnavailable, match="--serve"):
        trigger.create_flow_run({}, client=prefect_client(lambda request: httpx.Response(404, json={"detail": "Not found"})))

    def refuse(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(trigger.OrchestratorUnavailable, match="ConnectError"):
        trigger.create_flow_run({}, client=prefect_client(refuse))


def test_the_trigger_and_the_reads_do_not_import_prefect():
    """La API importa estos módulos: Prefect, al importarse, cambiaría su configuración de logging."""
    code = "import sys, brasaland_pipelines.trigger, brasaland_pipelines.repository; assert 'prefect' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], check=True)


def test_the_latest_run_is_the_most_recently_created(database):
    now = datetime.now(UTC)
    with database.begin() as conn:
        for minutes, status in ((60, "completed"), (5, "failed")):
            conn.execute(
                insert(repository.pipeline_runs).values(
                    id=uuid4(), pipeline=repository.PIPELINE, trigger="scheduled", week_from=WEEK, week_to=WEEK,
                    status=status, created_at=now - timedelta(minutes=minutes), issues={},
                )
            )
        assert repository.read_latest_pipeline_run(conn)["status"] == "failed"


def weekly_row(code, country, currency, week=WEEK, purchase=0.0):
    return {
        "location_id": code, "country": country, "week_start": week, "total_purchase_cost": purchase,
        "total_waste_cost": 0.0, "waste_ratio": 0.0, "stockout_events_count": 0,
        "price_alert_events_count": 0, "currency": currency,
    }


def test_reads_a_week_with_location_names_ordered_by_country_and_location(database):
    rows = pd.DataFrame(
        [
            weekly_row("miami_doral", "US", "USD", purchase=45.0),
            weekly_row("medellin_envigado", "CO", "COP", purchase=360000.0),
            weekly_row("medellin_centro", "CO", "COP"),
            weekly_row("medellin_centro", "CO", "COP", week=date(2026, 11, 9)),
        ]
    )
    with database.begin() as conn:
        repository.upsert_weekly_location_performance(conn, rows)

    with database.connect() as conn:
        latest_week, latest = repository.read_weekly_location_performance(conn)
        older_week, older = repository.read_weekly_location_performance(conn, date(2026, 11, 9))
        missing = repository.read_weekly_location_performance(conn, date(2026, 11, 2))

    assert latest_week == WEEK
    assert [row["location_id"] for row in latest] == ["medellin_centro", "medellin_envigado", "miami_doral"]
    assert latest[1]["location_name"] == "Medellin Envigado"
    assert latest[1]["total_purchase_cost"] == 360000.0
    assert (older_week, len(older)) == (date(2026, 11, 9), 1)
    assert missing is None


def test_without_any_computed_week_there_is_nothing_to_read(database):
    with database.connect() as conn:
        assert repository.read_weekly_location_performance(conn) is None


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgresql://u:p@h:5432/postgres", "postgresql+psycopg2://u:p@h:5432/postgres"),
        ("postgres://u:p@h:5432/postgres", "postgresql+psycopg2://u:p@h:5432/postgres"),
        ("postgresql+psycopg2://u:p@h/postgres", "postgresql+psycopg2://u:p@h/postgres"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_the_supabase_url_uses_the_installed_psycopg2_driver(url, expected):
    # SQLAlchemy 2.1 elige psycopg (v3) para postgresql://, que no está instalado.
    assert repository.with_psycopg2_driver(url) == expected
    if url.startswith("postgres"):
        assert repository.create_reporting_engine(url).dialect.driver == "psycopg2"
