"""Período, clave de deduplicación y argumentos de la tarea del reporte técnico (`app/domains/telemetry/report.py`)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.errors import ApiError
from app.domains.telemetry.report import (
    MAX_WINDOW,
    ReportRequest,
    parse_instant,
    resolve_period,
    task_kwargs,
)

NOW = datetime(2026, 11, 20, 10, 30, tzinfo=UTC)


# --- parse_instant ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-11-14", datetime(2026, 11, 14, tzinfo=UTC)),
        ("2026-11-14T08:00:00Z", datetime(2026, 11, 14, 8, tzinfo=UTC)),
        ("2026-11-14T08:00:00", datetime(2026, 11, 14, 8, tzinfo=UTC)),
        ("2026-11-14T08:00:00+02:00", datetime(2026, 11, 14, 6, tzinfo=UTC)),
        # Un + sin codificar en la URL llega como espacio.
        ("2026-11-14T08:00:00 02:00", datetime(2026, 11, 14, 6, tzinfo=UTC)),
        ("  2026-11-14  ", datetime(2026, 11, 14, tzinfo=UTC)),
    ],
)
def test_parse_instant_reads_iso_8601_into_utc(raw, expected):
    value = parse_instant(raw, "start_date")

    assert value == expected
    assert value.tzinfo == UTC


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_parse_instant_treats_empty_as_not_given(raw):
    assert parse_instant(raw, "start_date") is None


@pytest.mark.parametrize("raw", ["ayer", "2026-13-01", "14/11/2026", "2026-11-14T25:00:00Z"])
def test_parse_instant_rejects_malformed_dates_with_422(raw):
    with pytest.raises(ApiError) as error:
        parse_instant(raw, "end_date")

    assert (error.value.status_code, error.value.code) == (422, "invalid_date")
    assert "end_date" in error.value.message


# --- resolve_period ---------------------------------------------------------------------------------------


def test_without_parameters_the_period_is_the_last_7_days():
    assert resolve_period(ReportRequest(None, None), NOW) == (NOW - timedelta(days=7), NOW)


def test_with_only_end_the_period_is_the_7_days_before_it():
    end = datetime(2026, 11, 10, tzinfo=UTC)

    assert resolve_period(ReportRequest(None, end), NOW) == (datetime(2026, 11, 3, tzinfo=UTC), end)


def test_with_only_start_the_period_runs_until_now():
    start = datetime(2026, 11, 1, tzinfo=UTC)

    assert resolve_period(ReportRequest(start, None), NOW) == (start, NOW)


def test_explicit_parameters_are_used_as_given():
    start, end = datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 2, tzinfo=UTC)

    assert resolve_period(ReportRequest(start, end), NOW) == (start, end)


@pytest.mark.parametrize(
    "request_",
    [
        ReportRequest(datetime(2026, 11, 2, tzinfo=UTC), datetime(2026, 11, 2, tzinfo=UTC)),
        ReportRequest(datetime(2026, 11, 3, tzinfo=UTC), datetime(2026, 11, 2, tzinfo=UTC)),
        ReportRequest(NOW + timedelta(days=1), None),
    ],
)
def test_a_start_that_is_not_before_the_end_is_422(request_):
    with pytest.raises(ApiError) as error:
        resolve_period(request_, NOW)

    assert (error.value.status_code, error.value.code) == (422, "invalid_period")


def test_the_period_can_be_90_days_but_not_more():
    end = datetime(2026, 11, 20, tzinfo=UTC)
    assert resolve_period(ReportRequest(end - MAX_WINDOW, end), NOW) == (end - MAX_WINDOW, end)

    with pytest.raises(ApiError) as error:
        resolve_period(ReportRequest(end - MAX_WINDOW - timedelta(seconds=1), end), NOW)

    assert (error.value.status_code, error.value.code) == (422, "period_too_long")


# --- Clave de deduplicación (antes, la de la cache) ------------------------------------------------------


def test_the_dedupe_key_uses_the_parameters_received_not_the_resolved_period():
    assert ReportRequest(None, None).dedupe_key == "now|now"
    assert ReportRequest(datetime(2026, 11, 14, tzinfo=UTC), None).dedupe_key == "2026-11-14T00:00:00+00:00|now"


def test_equivalent_spellings_of_a_date_share_the_dedupe_key():
    spellings = ["2026-11-14", "2026-11-14T00:00:00Z", "2026-11-14T02:00:00+02:00"]
    keys = {ReportRequest(parse_instant(raw, "start_date"), None).dedupe_key for raw in spellings}

    assert len(keys) == 1


# --- Argumentos de la tarea -------------------------------------------------------------------------------


def test_task_kwargs_are_only_references_in_utc():
    start = datetime(2026, 11, 14, 8, tzinfo=timezone(timedelta(hours=2)))
    kwargs = task_kwargs(start, start + timedelta(days=1), "user-1")

    assert kwargs == {
        "start": "2026-11-14T06:00:00+00:00",
        "end": "2026-11-15T06:00:00+00:00",
        "requested_by": "user-1",
    }
