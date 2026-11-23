"""Endpoints de /reporting (services/reporting): KPIs semanales, última corrida y disparo manual.

Las tablas de `reporting` viven en una base SQLite adjunta (tests/conftest.py). Prefect se simula: el
disparo solo llega hasta `create_flow_run` de data/pipelines.
"""

import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pandas as pd
import pytest
from app.domains.users.models import Role
from brasaland_pipelines import repository, trigger
from sqlalchemy import insert, select, text

WEEK = date(2026, 11, 16)
PREVIOUS_WEEK = date(2026, 11, 9)
KPIS_URL = "/reporting/weekly-location-performance"
LATEST_URL = "/reporting/pipeline-runs/latest"
RUNS_URL = "/reporting/pipeline-runs"


def kpi_row(code, country, currency, week=WEEK, purchase=0.0, waste=0.0, stockouts=0, alerts=0):
    return {
        "location_id": code,
        "country": country,
        "week_start": week,
        "total_purchase_cost": purchase,
        "total_waste_cost": waste,
        "waste_ratio": round(waste / purchase, 4) if purchase else 0.0,
        "stockout_events_count": stockouts,
        "price_alert_events_count": alerts,
        "currency": currency,
    }


@pytest.fixture
def computed_weeks(inventory_engine):
    """Dos semanas calculadas, con tres locales en la última, como las escribe el pipeline."""
    rows = pd.DataFrame(
        [
            kpi_row("miami_doral", "US", "USD", purchase=45.0),
            kpi_row("medellin_envigado", "CO", "COP", purchase=1170000.0, waste=45900.0, stockouts=1, alerts=1),
            kpi_row("medellin_centro", "CO", "COP"),
            kpi_row("medellin_centro", "CO", "COP", week=PREVIOUS_WEEK, purchase=360000.0),
        ]
    )
    with inventory_engine.begin() as conn:
        repository.upsert_weekly_location_performance(conn, rows)


@pytest.fixture
def manager(make_user):
    return make_user("felipe@brasaland.com", role=Role.MANAGER)[1]


@pytest.fixture
def admin(make_user):
    return make_user("mariana@brasaland.com", role=Role.ADMIN)


# --- GET /reporting/weekly-location-performance ---------------------------------------------------


def test_returns_the_latest_computed_week_with_the_briefing_contract(api, computed_weeks, manager):
    response = api.get(KPIS_URL, headers=manager)

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == "2026-11-16"
    assert [row["location_id"] for row in body["locations"]] == ["medellin_centro", "medellin_envigado", "miami_doral"]
    assert body["locations"][1] == {
        "location_id": "medellin_envigado",
        "location_name": "Medellín Envigado",
        "country": "CO",
        "total_purchase_cost": 1170000.0,
        "total_waste_cost": 45900.0,
        "waste_ratio": 0.0392,
        "stockout_events_count": 1,
        "price_alert_events_count": 1,
        "currency": "COP",
    }
    assert body["locations"][2]["currency"] == "USD"


def test_returns_a_given_week(api, computed_weeks, manager):
    body = api.get(KPIS_URL, params={"week_start": "2026-11-09"}, headers=manager).json()

    assert body["week_start"] == "2026-11-09"
    assert [(row["location_id"], row["total_purchase_cost"]) for row in body["locations"]] == [("medellin_centro", 360000.0)]


def test_the_week_must_be_a_monday(api, computed_weeks, manager):
    response = api.get(KPIS_URL, params={"week_start": "2026-11-17"}, headers=manager)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_week_start"
    assert api.get(KPIS_URL, params={"week_start": "16/11/2026"}, headers=manager).status_code == 422


def test_a_week_that_is_not_computed_is_a_404(api, computed_weeks, manager):
    response = api.get(KPIS_URL, params={"week_start": "2026-11-02"}, headers=manager)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "week_not_computed"


def test_without_any_computed_week_it_is_a_404(api, manager):
    response = api.get(KPIS_URL, headers=manager)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "week_not_computed"


def test_the_kpis_are_cached_for_five_minutes_per_week(api, computed_weeks, manager, inventory_engine):
    first = api.get(KPIS_URL, headers=manager)
    with inventory_engine.begin() as conn:
        repository.upsert_weekly_location_performance(conn, pd.DataFrame([kpi_row("medellin_centro", "CO", "COP", purchase=1.0)]))
    second = api.get(KPIS_URL, headers=manager)

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert second.json() == first.json()


def test_missing_reporting_tables_are_a_503(api, manager, inventory_engine, caplog):
    with inventory_engine.begin() as conn:
        conn.execute(text("DROP TABLE reporting.weekly_location_performance"))

    response = api.get(KPIS_URL, headers=manager)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "reporting_unavailable"
    assert "005_reporting.sql" in caplog.text


def test_only_admins_and_managers_read_the_kpis(api, computed_weeks, make_user, admin):
    _, user = make_user("cocina@brasaland.com")

    assert api.get(KPIS_URL).status_code == 401
    assert api.get(KPIS_URL, headers=user).status_code == 403
    assert api.get(KPIS_URL, headers=admin[1]).status_code == 200


# --- GET /reporting/pipeline-runs/latest ----------------------------------------------------------


def add_run(engine, minutes_ago, status="completed", **values):
    run_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            insert(repository.pipeline_runs).values(
                id=run_id,
                pipeline=repository.PIPELINE,
                trigger="scheduled",
                week_from=date(2026, 10, 26),
                week_to=WEEK,
                status=status,
                created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
                **{"issues": {}, **values},
            )
        )
    return run_id


def test_returns_the_status_and_metadata_of_the_latest_run(api, manager, inventory_engine):
    add_run(inventory_engine, 90, status="failed")
    started = datetime.now(UTC) - timedelta(minutes=10)
    run_id = add_run(
        inventory_engine, 10,
        started_at=started, finished_at=started + timedelta(seconds=42), events_read=8, events_rejected=1,
        events_discarded=1, issues={"country_mismatch": 1, "price_decrease": 1}, rows_written=56,
        requested_by=uuid4(), prefect_flow_run_id=uuid4(),
    )

    response = api.get(LATEST_URL, headers=manager)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(run_id)
    assert (body["status"], body["trigger"], body["week_from"], body["week_to"]) == ("completed", "scheduled", "2026-10-26", "2026-11-16")
    assert body["started_at"] is not None and body["finished_at"] is not None
    assert (body["events_read"], body["events_rejected"], body["events_discarded"], body["rows_written"]) == (8, 1, 1, 56)
    assert body["issues"] == {"country_mismatch": 1, "price_decrease": 1}
    assert "requested_by" not in body and "prefect_flow_run_id" not in body


def test_without_runs_it_is_a_404(api, manager):
    response = api.get(LATEST_URL, headers=manager)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_pipeline_runs"


def test_only_admins_and_managers_read_the_runs(api, make_user, inventory_engine):
    add_run(inventory_engine, 5)
    _, user = make_user("cocina@brasaland.com")

    assert api.get(LATEST_URL).status_code == 401
    assert api.get(LATEST_URL, headers=user).status_code == 403


# --- POST /reporting/pipeline-runs ----------------------------------------------------------------


@pytest.fixture
def prefect(monkeypatch):
    """Prefect configurado; `create_flow_run` simulado guarda los parámetros de cada corrida pedida."""
    calls = []
    monkeypatch.setenv("PREFECT_API_URL", "http://prefect-server:4200/api")

    def fake_create_flow_run(parameters):
        calls.append(parameters)
        return uuid4()

    monkeypatch.setattr(trigger, "create_flow_run", fake_create_flow_run)
    return calls


def stored_run(engine, run_id):
    with engine.connect() as conn:
        return conn.execute(select(repository.pipeline_runs).where(repository.pipeline_runs.c.id == UUID(run_id))).mappings().one()


def test_an_admin_queues_a_manual_run_of_the_last_four_closed_weeks(api, admin, prefect, inventory_engine):
    user, headers = admin

    response = api.post(RUNS_URL, headers=headers)

    assert response.status_code == 202
    body = response.json()
    assert (body["status"], body["trigger"]) == ("pending", "manual")
    week_from, week_to = date.fromisoformat(body["week_from"]), date.fromisoformat(body["week_to"])
    this_monday = date.today() - timedelta(days=date.today().weekday())
    assert week_to == this_monday - timedelta(days=7)
    assert week_from == week_to - timedelta(days=21)
    assert prefect == [{"week_from": body["week_from"], "week_to": body["week_to"], "trigger": "manual", "run_id": body["id"]}]
    run = stored_run(inventory_engine, body["id"])
    assert run["requested_by"] == UUID(user.id)
    assert run["prefect_flow_run_id"] is not None


def test_a_backfill_range_can_be_requested(api, admin, prefect):
    response = api.post(RUNS_URL, json={"week_from": "2026-09-07", "week_to": "2026-09-21"}, headers=admin[1])

    assert response.status_code == 202
    assert (response.json()["week_from"], response.json()["week_to"]) == ("2026-09-07", "2026-09-21")


@pytest.mark.parametrize(
    "body",
    [
        {"week_from": "2026-09-08", "week_to": "2026-09-21"},  # no es lunes
        {"week_from": "2026-09-21", "week_to": "2026-09-07"},  # al revés
        {"week_from": "2025-01-06", "week_to": "2026-09-21"},  # más de 26 semanas
    ],
)
def test_an_invalid_range_is_a_422_and_writes_nothing(api, admin, prefect, body):
    response = api.post(RUNS_URL, json=body, headers=admin[1])

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_week_range"
    assert prefect == []


def test_the_current_week_cannot_be_requested(api, admin, prefect):
    this_monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    response = api.post(RUNS_URL, json={"week_from": this_monday, "week_to": this_monday}, headers=admin[1])

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_week_range"


def test_unknown_fields_are_rejected(api, admin, prefect):
    response = api.post(RUNS_URL, json={"weeks": 4}, headers=admin[1])

    assert response.status_code == 422
    assert prefect == []


def test_a_second_active_run_is_a_409(api, admin, prefect):
    assert api.post(RUNS_URL, headers=admin[1]).status_code == 202

    response = api.post(RUNS_URL, headers=admin[1])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "pipeline_run_in_progress"
    assert len(prefect) == 1


def test_without_prefect_configured_it_is_a_503_and_nothing_is_written(api, admin, monkeypatch, manager):
    monkeypatch.delenv("PREFECT_API_URL", raising=False)

    response = api.post(RUNS_URL, headers=admin[1])

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "orchestrator_unavailable"
    assert api.get(LATEST_URL, headers=manager).status_code == 404


def test_if_prefect_does_not_answer_the_run_is_closed_as_failed(api, admin, monkeypatch, manager):
    monkeypatch.setenv("PREFECT_API_URL", "http://prefect-server:4200/api")

    def unreachable(parameters):
        raise trigger.OrchestratorUnavailable("Prefect no respondió: ConnectError.")

    monkeypatch.setattr(trigger, "create_flow_run", unreachable)

    response = api.post(RUNS_URL, headers=admin[1])

    assert response.status_code == 503
    latest = api.get(LATEST_URL, headers=manager).json()
    assert latest["status"] == "failed"
    assert latest["error_message"].startswith("orchestrator_unavailable")


def test_only_admins_trigger_runs(api, manager, prefect):
    assert api.post(RUNS_URL).status_code == 401
    assert api.post(RUNS_URL, headers=manager).status_code == 403
    assert prefect == []


# --- La API no importa Prefect ----------------------------------------------------------------------


def test_the_api_does_not_import_prefect():
    """Prefect, al importarse, reconfigura el logging del proceso (el raíz y el de uvicorn)."""
    env = {**os.environ, "SECRET_KEY": "clave-de-pruebas-solo-para-pytest-0123456789", "ACCESS_TOKEN_EXPIRE_MINUTES": "30"}
    code = "import sys, app.main; assert 'prefect' not in sys.modules, 'app.main importa prefect'"
    subprocess.run([sys.executable, "-c", code], check=True, env=env)
