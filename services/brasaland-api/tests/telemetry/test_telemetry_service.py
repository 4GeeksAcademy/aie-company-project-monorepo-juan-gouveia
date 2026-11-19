"""De evento a fila: `service`, `value`, `message` y `tags` (plan de telemetría, sección 14.2)."""

from decimal import Decimal

import pytest

from app.domains.telemetry.schemas import TelemetryEvent
from app.domains.telemetry.service import (
    MESSAGE_MAX_LENGTH,
    build_message,
    build_value,
    check_properties,
    parse_batch,
    to_row,
)
from tests.telemetry.helpers import make_event


def event(event_type: str = "page_viewed", **changes) -> TelemetryEvent:
    return TelemetryEvent.model_validate(make_event(event_type, **changes))


@pytest.mark.parametrize(("source", "service"), [("browser", "backoffice"), ("api", "api"), ("bff", "bff"), ("process", "process")])
def test_service_comes_from_the_source_of_the_envelope(source, service):
    assert to_row(event(source=source))["service"] == service


def test_tags_carry_the_properties_and_five_envelope_fields_with_nulls():
    row = to_row(event("login_failed", sessionId=None, userId=None, requestId=None))

    assert row["tags"] == {
        "failure_reason": "invalid_credentials",
        "session_id": None,
        "user_id": None,
        "request_id": None,
        "schema_version": "2.0.0",
        "environment": "development",
    }
    assert "eventId" not in row["tags"] and "source" not in row["tags"]


@pytest.mark.parametrize(
    ("properties", "expected"),
    [({"n": 18.5}, Decimal("18.5")), ({"n": 3}, Decimal("3")), ({"n": None}, None), ({}, None), ({"n": True}, None), ({"n": "4"}, None)],
)
def test_value_only_copies_numbers(properties, expected):
    assert build_value("n", properties) == expected


def test_value_is_null_when_the_event_has_no_main_metric():
    assert build_value(None, {"n": 1}) is None


@pytest.mark.parametrize(
    ("properties", "expected"),
    [
        ({"a": 12.0, "b": "kg"}, "12 kg"),
        ({"a": None, "b": ""}, "— —"),
        ({"a": True, "b": False}, "sí no"),
        ({"a": ["carne", "pollo"], "b": []}, "carne, pollo —"),
        ({}, "— —"),
    ],
)
def test_message_fills_the_holes_of_the_template(properties, expected):
    assert build_message("{a} {b}", properties) == expected


def test_message_is_cut_to_200_characters():
    message = build_message("{a}", {"a": "x" * 500})

    assert len(message) == MESSAGE_MAX_LENGTH
    assert message.endswith("…")


def test_properties_must_follow_the_catalog():
    assert check_properties(event("page_viewed")) is None
    unknown = TelemetryEvent.model_validate({**make_event(), "event_type": "pizza_ordered"})
    assert check_properties(unknown) == "event_type fuera del catálogo"
    assert check_properties(event("login_failed", properties={})) == "properties.failure_reason: obligatoria"
    assert check_properties(event("login_failed", properties={"failure_reason": "x", "email": "a@b.c"})) == (
        "properties.email: fuera del allowlist"
    )


def test_optional_properties_can_be_left_out():
    properties = {"route": "/inventario", "navigation_type": "initial"}

    assert check_properties(event("page_viewed", properties=properties)) is None


def test_parse_batch_never_raises_and_keeps_the_order_of_the_valid_events():
    first, second = make_event("page_viewed"), make_event("login_failed")

    parsed = parse_batch([first, None, {"event_type": "login_failed"}, second])

    assert [str(e.eventId) for e in parsed.valid] == [first["eventId"], second["eventId"]]
    assert [(r.index, r.event_type) for r in parsed.rejections] == [(1, "?"), (2, "login_failed")]
