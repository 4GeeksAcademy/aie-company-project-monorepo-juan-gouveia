"""El flow completo y sus subflows contra SQLite: KPIs, log de corridas, idempotencia, resiliencia y caché."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from brasaland_pipelines import pipeline, repository
from brasaland_process import weekly_location_performance as process
from conftest import add_event, telemetry_events
from sqlalchemy import func, insert, select
from sqlalchemy.exc import OperationalError, ProgrammingError

WEEK_A = date(2026, 11, 9)
WEEK_B = date(2026, 11, 16)


def seed(engine):
    """Ocho eventos de production de dos semanas y un evento de development que no debe entrar."""
    add_event(engine, "inbound_order_created", timestamp="2026-11-10T15:00:00+00:00", order_id=1, quantity=10, unit_cost=36000)
    add_event(engine, "inbound_order_created", timestamp="2026-11-17T15:00:00+00:00", order_id=2, quantity=30, unit_cost=39000)
    add_event(engine, "stock_waste_registered", timestamp="2026-11-18T09:00:00+00:00", order_id=3, quantity=1.2, unit_cost=38250, reason="expired")
    add_event(engine, "stock_threshold_triggered", timestamp="2026-11-18T09:00:01+00:00", trigger_order_id=3, quantity=38, threshold_quantity=40)
    add_event(engine, "ingredient_price_variance_detected", timestamp="2026-11-17T15:00:01+00:00", order_id=2, variance_pct=12.5, unit_cost=39000)
    add_event(engine, "ingredient_price_variance_detected", timestamp="2026-11-17T16:00:00+00:00", order_id=4, variance_pct=-11.0, unit_cost=30000)
    add_event(engine, "inbound_order_created", timestamp="2026-11-11T12:00:00+00:00", location_id=10, order_id=5, quantity=10, unit_cost=4.5)
    add_event(engine, "stock_waste_registered", timestamp="2026-11-19T12:00:00+00:00", location_id=11, country="CO", order_id=6, quantity=1, unit_cost=4.5)
    add_event(engine, "inbound_order_created", timestamp="2026-11-12T12:00:00+00:00", environment="development", order_id=7, quantity=99, unit_cost=99)


def run(**kwargs):
    return pipeline.weekly_location_performance_flow(week_from=WEEK_A, week_to=WEEK_B, trigger="manual", **kwargs)


def table(engine):
    columns = [c for c in repository.weekly_location_performance.c if c.name not in ("id", "computed_at")]
    with engine.connect() as conn:
        rows = conn.execute(select(*columns).order_by("location_id", "week_start")).mappings().all()
    return [dict(row) for row in rows]


def kpis(engine, code, week):
    [match] = [row for row in table(engine) if row["location_id"] == code and row["week_start"] == week]
    return match


def runs(engine):
    with engine.connect() as conn:
        rows = conn.execute(select(repository.pipeline_runs).order_by(repository.pipeline_runs.c.created_at)).mappings().all()
    return [dict(row) for row in rows]


def test_writes_the_five_kpis_and_logs_the_run(database):
    seed(database)
    with database.connect() as conn:
        events_before = conn.execute(select(func.count()).select_from(telemetry_events)).scalar_one()

    summary = run()

    assert summary["status"] == "completed"
    assert summary["rows_written"] == 28
    assert kpis(database, "medellin_envigado", WEEK_B) == {
        "location_id": "medellin_envigado",
        "country": "CO",
        "week_start": WEEK_B,
        "total_purchase_cost": 1170000.0,
        "total_waste_cost": 45900.0,
        "waste_ratio": 0.0392,
        "stockout_events_count": 1,
        "price_alert_events_count": 1,
        "currency": "COP",
    }
    assert kpis(database, "medellin_envigado", WEEK_A)["total_purchase_cost"] == 360000.0
    assert kpis(database, "miami_doral", WEEK_A)["total_purchase_cost"] == 45.0
    assert kpis(database, "miami_doral", WEEK_A)["currency"] == "USD"
    assert kpis(database, "miami_hialeah", WEEK_B)["total_waste_cost"] == 0.0

    [logged] = runs(database)
    assert logged["status"] == "completed"
    assert logged["trigger"] == "manual"
    assert (logged["week_from"], logged["week_to"]) == (WEEK_A, WEEK_B)
    assert logged["started_at"] is not None and logged["finished_at"] >= logged["started_at"]
    assert (logged["events_read"], logged["events_rejected"], logged["events_discarded"]) == (8, 1, 1)
    assert logged["issues"] == {"country_mismatch": 1, "price_decrease": 1}
    assert logged["rows_written"] == 28
    assert logged["prefect_flow_run_id"] is not None
    assert logged["failed_task"] is None and logged["error_message"] is None

    with database.connect() as conn:
        assert conn.execute(select(func.count()).select_from(telemetry_events)).scalar_one() == events_before


def test_saves_the_raw_extract_without_personal_data_and_an_eval_snapshot(database):
    seed(database)

    summary = run()

    raw = pipeline.RAW_DIR / f"{summary['run_id']}.json"
    raw_text = raw.read_text(encoding="utf-8")
    assert len(json.loads(raw_text)["events"]) == 8
    for personal in ("user_id", "session_id", "request_id", "d445afb4"):
        assert personal not in raw_text

    snapshot = json.loads((pipeline.EVAL_DIR / f"{summary['run_id']}.json").read_text(encoding="utf-8"))
    assert all(snapshot["checks"].values()), snapshot["checks"]
    assert len(snapshot["rows"]) == 28


def test_running_twice_leaves_the_table_identical(database):
    seed(database)

    run()
    first = table(database)
    run()

    assert table(database) == first
    assert len(first) == 28
    assert [r["status"] for r in runs(database)] == ["completed", "completed"]


def test_a_late_event_rewrites_its_week_instead_of_adding_a_row(database):
    seed(database)
    run()

    add_event(database, "inbound_order_created", timestamp="2026-11-12T08:00:00+00:00", order_id=8, quantity=5, unit_cost=1000)
    run()

    assert kpis(database, "medellin_envigado", WEEK_A)["total_purchase_cost"] == 365000.0
    assert len(table(database)) == 28


def test_a_failed_load_closes_the_run_as_failed_and_keeps_the_table(database, monkeypatch):
    seed(database)
    run()
    before = table(database)

    def broken_upsert(conn, rows):
        raise ProgrammingError("INSERT INTO reporting.weekly_location_performance", {}, Exception("permission denied"))

    monkeypatch.setattr(repository, "upsert_weekly_location_performance", broken_upsert)

    with pytest.raises(ProgrammingError):
        run()

    failed = runs(database)[-1]
    assert failed["status"] == "failed"
    assert failed["failed_task"] == "upsert_weekly_location_performance"
    assert "ProgrammingError" in failed["error_message"]
    assert failed["events_read"] == 8
    assert table(database) == before


def test_optional_tasks_can_fail_without_stopping_the_run(database, monkeypatch, tmp_path):
    seed(database)
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("x")
    monkeypatch.setattr(pipeline, "RAW_DIR", blocked / "raw")
    monkeypatch.setattr(pipeline, "EVAL_DIR", blocked / "eval")

    summary = run()

    assert summary["status"] == "completed"
    assert summary["rows_written"] == 28
    logged = runs(database)[-1]
    assert logged["status"] == "completed"
    assert logged["issues"]["save_raw_extract_failed"] == 1
    assert logged["issues"]["export_eval_snapshot_failed"] == 1


def test_a_transient_database_error_is_retried(database, monkeypatch):
    seed(database)
    calls = {"n": 0}
    real_fetch = repository.fetch_business_events

    def flaky_fetch(conn, weeks, environment):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OperationalError("SELECT", {}, Exception("server closed the connection unexpectedly"))
        return real_fetch(conn, weeks, environment)

    monkeypatch.setattr(repository, "fetch_business_events", flaky_fetch)
    monkeypatch.setattr(pipeline, "extract_business_events", pipeline.extract_business_events.with_options(retry_delay_seconds=0))

    assert run()["status"] == "completed"
    assert calls["n"] == 2


def test_a_non_transient_error_is_not_retried_and_closes_the_run(database, monkeypatch):
    seed(database)
    calls = {"n": 0}

    def broken_fetch(conn, weeks, environment):
        calls["n"] += 1
        raise ProgrammingError("SELECT", {}, Exception('relation "telemetry_events" does not exist'))

    monkeypatch.setattr(repository, "fetch_business_events", broken_fetch)
    monkeypatch.setattr(pipeline, "extract_business_events", pipeline.extract_business_events.with_options(retry_delay_seconds=0))

    with pytest.raises(ProgrammingError):
        run()

    assert calls["n"] == 1
    failed = runs(database)[-1]
    assert (failed["status"], failed["failed_task"]) == ("failed", "extract_business_events")


@pytest.mark.parametrize(
    "message",
    [
        'FATAL:  password authentication failed for user "reporting_pipeline"',
        "FATAL:  (ENOTFOUND) tenant/user reporting_pipeline.abc not found",
    ],
)
def test_a_credential_error_is_not_retried(database, monkeypatch, message):
    # psycopg2 lo da como OperationalError, sin SQLSTATE: reintentarlo no sirve y el pooler puede
    # bloquear la IP por intentos fallidos.
    seed(database)
    calls = {"n": 0}

    def rejected_fetch(conn, weeks, environment):
        calls["n"] += 1
        raise OperationalError("SELECT", {}, Exception(message))

    monkeypatch.setattr(repository, "fetch_business_events", rejected_fetch)
    monkeypatch.setattr(pipeline, "extract_business_events", pipeline.extract_business_events.with_options(retry_delay_seconds=0))

    with pytest.raises(OperationalError):
        run()

    assert calls["n"] == 1
    assert runs(database)[-1]["failed_task"] == "extract_business_events"


def test_the_transformation_is_cached_while_its_inputs_do_not_change(database, monkeypatch):
    seed(database)
    calls = {"n": 0}
    real_prepare = process.prepare_weekly_location_facts

    def counting_prepare(events, locations, weeks):
        calls["n"] += 1
        return real_prepare(events, locations, weeks)

    monkeypatch.setattr(process, "prepare_weekly_location_facts", counting_prepare)

    run()
    run()
    assert calls["n"] == 1

    add_event(database, "inbound_order_created", timestamp="2026-11-12T08:00:00+00:00", order_id=9, quantity=1, unit_cost=1000)
    run()
    assert calls["n"] == 2
    assert len(table(database)) == 28


def test_refuses_to_start_while_another_run_is_active(database):
    with database.begin() as conn:
        conn.execute(
            insert(repository.pipeline_runs).values(
                id=uuid4(), pipeline=repository.PIPELINE, trigger="scheduled", week_from=WEEK_A, week_to=WEEK_B,
                status="running", created_at=datetime.now(UTC), issues={},
            )
        )

    with pytest.raises(repository.PipelineRunInProgress):
        run()

    assert len(runs(database)) == 1


def test_an_abandoned_run_is_closed_and_does_not_block_the_next(database):
    stale_id = uuid4()
    with database.begin() as conn:
        conn.execute(
            insert(repository.pipeline_runs).values(
                id=stale_id, pipeline=repository.PIPELINE, trigger="scheduled", week_from=WEEK_A, week_to=WEEK_B,
                status="running", created_at=datetime.now(UTC) - timedelta(hours=2), issues={},
            )
        )

    assert run()["status"] == "completed"

    stale = next(r for r in runs(database) if r["id"] == stale_id)
    assert (stale["status"], stale["error_message"]) == ("failed", "abandoned")


def test_completes_a_manual_run_registered_as_pending(database):
    with database.begin() as conn:
        run_id = repository.create_pending_run(conn, week_from=WEEK_A, week_to=WEEK_B, requested_by=None, now=datetime.now(UTC))

    summary = run(run_id=run_id)

    assert summary["run_id"] == str(run_id)
    [logged] = runs(database)
    assert (logged["id"], logged["status"]) == (run_id, "completed")
    assert logged["prefect_flow_run_id"] is not None


def test_the_command_line_runs_the_flow(database, capsys):
    seed(database)

    assert pipeline.main(["--week-from", "2026-11-09", "--week-to", "2026-11-16"]) == 0

    assert json.loads(capsys.readouterr().out)["rows_written"] == 28


def test_the_command_line_rejects_an_invalid_range_without_creating_a_run(database, capsys):
    assert pipeline.main(["--week-from", "2026-11-10"]) == 2

    assert "lunes" in capsys.readouterr().err
    assert runs(database) == []


# --- Subflows -------------------------------------------------------------------------------------


def test_a_failure_inside_the_transformation_names_its_task(database, monkeypatch):
    seed(database)

    def broken_ratio(rows):
        raise ValueError("waste_ratio: los costes de compra y de merma deben ser números no negativos.")

    monkeypatch.setattr(process, "compute_waste_ratio", broken_ratio)

    with pytest.raises(ValueError, match="waste_ratio"):
        run()

    failed = runs(database)[-1]
    assert (failed["status"], failed["failed_task"]) == ("failed", "compute_waste_ratio")


def test_the_extraction_subflow_runs_on_its_own(database):
    seed(database)

    sources = pipeline.extract_weekly_location_performance_sources([WEEK_A, WEEK_B], "production")

    assert len(sources.business_events) == 8
    assert list(sources.business_events.columns) == ["id", "timestamp", "event_type", "tags"]
    assert len(sources.locations) == 14
    assert sources.telemetry_events_per_week == {WEEK_A: 2, WEEK_B: 6}
    assert runs(database) == []


def test_the_transformation_subflow_runs_on_its_own_without_a_database():
    events = pd.DataFrame(
        [
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "timestamp": "2026-11-17T15:00:00+00:00",
                "event_type": "inbound_order_created",
                "tags": {"location_id": 1, "country": "CO", "currency": "COP", "order_id": 1, "quantity": 4, "unit_cost": 250},
            }
        ]
    )
    locations = pd.DataFrame(
        {"id": [1, 10], "code": ["medellin_centro", "miami_doral"], "country": ["CO", "US"], "currency": ["COP", "USD"]}
    )

    result = pipeline.transform_weekly_location_performance(events, locations, [WEEK_B])

    assert result.rows["location_id"].tolist() == ["medellin_centro", "miami_doral"]
    assert result.rows["total_purchase_cost"].tolist() == [1000.0, 0.0]
    assert result.events_read == 1


def test_the_load_subflow_runs_on_its_own_and_is_idempotent(database):
    rows = pd.DataFrame(
        [
            {
                "location_id": "medellin_centro", "country": "CO", "week_start": WEEK_B,
                "total_purchase_cost": 850.0, "total_waste_cost": 106.25, "waste_ratio": 0.125,
                "stockout_events_count": 1, "price_alert_events_count": 1, "currency": "COP",
            }
        ]
    )

    assert pipeline.load_weekly_location_performance(rows) == 1
    assert pipeline.load_weekly_location_performance(rows) == 1
    assert len(table(database)) == 1
    assert kpis(database, "medellin_centro", WEEK_B)["waste_ratio"] == 0.125


def test_the_optional_subflows_run_on_their_own(database):
    seed(database)
    events = pipeline.extract_business_events.fn([WEEK_A, WEEK_B], "production")
    run_id = uuid4()

    raw = pipeline.archive_weekly_location_performance_extract(events, run_id, [WEEK_A, WEEK_B], "production")
    assert json.loads(Path(raw).read_text(encoding="utf-8"))["run_id"] == str(run_id)

    locations = pipeline.extract_locations.fn()
    result = pipeline.transform_weekly_location_performance(events, locations, [WEEK_A, WEEK_B])
    snapshot = pipeline.export_weekly_location_performance_eval(result, 28, run_id, [WEEK_A, WEEK_B])
    assert all(json.loads(Path(snapshot).read_text(encoding="utf-8"))["checks"].values())


# --- Señales de silencio --------------------------------------------------------------------------


def test_silent_weeks_are_logged_without_failing_the_run(database):
    seed(database)
    week_without_telemetry = date(2026, 10, 26)
    week_without_business_events = date(2026, 11, 2)
    add_event(database, "page_viewed", timestamp="2026-11-04T10:00:00+00:00", path="/inventario")

    summary = pipeline.weekly_location_performance_flow(
        week_from=week_without_telemetry, week_to=WEEK_B, trigger="manual"
    )

    assert summary["status"] == "completed"
    assert summary["issues"]["weeks_without_telemetry"] == 1
    assert summary["issues"]["weeks_without_business_events"] == 1
    assert runs(database)[-1]["issues"]["weeks_without_telemetry"] == 1
    assert kpis(database, "medellin_envigado", week_without_business_events)["total_purchase_cost"] == 0.0


# --- resolve_weeks --------------------------------------------------------------------------------

WEDNESDAY = date(2026, 11, 25)


def weeks(**kwargs):
    params = {"today": WEDNESDAY, "week_from": None, "week_to": None, "lookback_weeks": 4, "max_backfill_weeks": 26}
    return pipeline.resolve_weeks.fn(**{**params, **kwargs})


def test_by_default_the_last_four_closed_weeks():
    assert weeks() == [date(2026, 10, 26), date(2026, 11, 2), date(2026, 11, 9), date(2026, 11, 16)]


def test_the_current_week_only_with_the_verification_option():
    assert weeks(include_current_week=True)[-1] == date(2026, 11, 23)
    assert weeks(week_from=date(2026, 11, 23), week_to=date(2026, 11, 23), include_current_week=True) == [date(2026, 11, 23)]
    with pytest.raises(ValueError, match="en curso"):
        weeks(week_from=date(2026, 11, 23), week_to=date(2026, 11, 23))


def test_a_backfill_range_is_validated():
    assert weeks(week_from=date(2026, 9, 7), week_to=date(2026, 9, 21)) == [date(2026, 9, 7), date(2026, 9, 14), date(2026, 9, 21)]
    assert weeks(week_from=date(2026, 9, 7)) == [date(2026, 9, 7)]
    with pytest.raises(ValueError, match="lunes"):
        weeks(week_from=date(2026, 9, 8), week_to=date(2026, 9, 21))
    with pytest.raises(ValueError, match="posterior"):
        weeks(week_from=date(2026, 9, 21), week_to=date(2026, 9, 7))
    with pytest.raises(ValueError, match="máximo"):
        weeks(week_from=date(2025, 1, 6), week_to=date(2026, 11, 16))
