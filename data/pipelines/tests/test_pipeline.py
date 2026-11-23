"""El flow completo contra SQLite: KPIs, log de corridas, idempotencia, resiliencia y caché."""

import json
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from brasaland_pipelines import pipeline, repository
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
    assert failed["failed_task"] == "load_weekly_location_performance"
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


def test_the_transformation_is_cached_while_its_inputs_do_not_change(database, monkeypatch):
    seed(database)
    calls = {"n": 0}
    real_build = pipeline.build_weekly_location_performance

    def counting_build(events, locations, weeks):
        calls["n"] += 1
        return real_build(events, locations, weeks)

    monkeypatch.setattr(pipeline, "build_weekly_location_performance", counting_build)

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
