"""`TelemetryEvent` y `TelemetryBatch`: el envelope del plan de telemetría, sin campos extra."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domains.telemetry.schemas import MAX_BATCH_EVENTS, TelemetryBatch, TelemetryEvent
from tests.telemetry.helpers import EVENT

SCHEMAS = Path(__file__).resolve().parents[4] / "docs" / "telemetry" / "event-schemas.json"

ENVELOPE_FIELDS = {"eventId", "timestamp", "sessionId", "userId", "event_type", "schemaVersion", "requestId", "properties"}


def with_changes(**changes) -> dict:
    event = deepcopy(EVENT)
    event.update(changes)
    return event


def error_fields(data: dict) -> set[str]:
    with pytest.raises(ValidationError) as info:
        TelemetryEvent.model_validate(data)
    return {str(error["loc"][0]) for error in info.value.errors()}


def test_model_has_the_envelope_fields_of_the_plan():
    # Los 8 campos del enunciado, más los 2 que añade el plan.
    assert set(TelemetryEvent.model_fields) == ENVELOPE_FIELDS | {"source", "environment"}


def test_accepts_a_complete_event():
    event = TelemetryEvent.model_validate(EVENT)
    assert event.event_type == "inbound_order_created"
    assert event.timestamp.isoformat() == "2026-11-19T10:15:30.123000+00:00"
    assert event.properties["order_id"] == 7824


def test_accepts_null_session_user_and_request():
    event = TelemetryEvent.model_validate(with_changes(sessionId=None, userId=None, requestId=None))
    assert (event.sessionId, event.userId, event.requestId) == (None, None, None)


def test_accepts_every_example_of_event_schemas_json():
    # El modelo y el esquema JSON describen el mismo envelope: los 44 ejemplos aprobados son válidos.
    schemas = json.loads(SCHEMAS.read_text(encoding="utf-8"))
    examples = [example for event in schemas["definitions"]["events"].values() for example in event["examples"]]
    assert len(examples) == 44
    for example in examples:
        TelemetryEvent.model_validate(example)


@pytest.mark.parametrize("field", sorted(ENVELOPE_FIELDS | {"source", "environment"}))
def test_every_field_is_required(field):
    data = deepcopy(EVENT)
    del data[field]
    assert field in error_fields(data)


def test_rejects_fields_outside_the_envelope():
    assert "email" in error_fields(with_changes(email="ana@brasaland.com"))


@pytest.mark.parametrize(
    "timestamp",
    ["2026-11-19T10:15:30Z", "2026-11-19T10:15:30.123+02:00", "2026-11-19 10:15:30.123", "19/11/2026", 1763547330123],
)
def test_timestamp_must_be_utc_iso_8601_with_milliseconds(timestamp):
    assert "timestamp" in error_fields(with_changes(timestamp=timestamp))


@pytest.mark.parametrize("field", ["eventId", "sessionId", "userId", "requestId"])
def test_identifiers_must_be_uuid_v4(field):
    assert field in error_fields(with_changes(**{field: "no-es-un-uuid"}))
    # UUID válido, pero de la versión 1.
    assert field in error_fields(with_changes(**{field: "6ba7b810-9dad-11d1-80b4-00c04fd430c8"}))


@pytest.mark.parametrize("event_type", ["InboundOrderCreated", "inbound", "inbound-order-created", "inbound_order_", ""])
def test_event_type_must_be_entity_action_in_snake_case(event_type):
    assert "event_type" in error_fields(with_changes(event_type=event_type))


@pytest.mark.parametrize("version", ["1", "1.0", "v1.0.0", "1.0.0-beta"])
def test_schema_version_must_be_semver(version):
    assert "schemaVersion" in error_fields(with_changes(schemaVersion=version))


def test_properties_must_be_an_object():
    assert "properties" in error_fields(with_changes(properties=["order_id"]))


@pytest.mark.parametrize(("field", "value"), [("source", "mobile"), ("environment", "test")])
def test_source_and_environment_only_take_the_values_of_the_plan(field, value):
    assert field in error_fields(with_changes(**{field: value}))


# --- Lote ------------------------------------------------------------------------------------------


def test_batch_reads_events_without_validating_them():
    # Fase de almacenamiento: cada evento se valida después, por separado (plan, sección 14.3).
    batch = TelemetryBatch.model_validate({"events": [EVENT, {"eventId": "x"}, 3, None]})
    assert batch.events == [EVENT, {"eventId": "x"}, 3, None]


def test_batch_accepts_an_empty_list_and_leaves_the_maximum_to_the_receiver():
    assert TelemetryBatch.model_validate({"events": []}).events == []
    assert len(TelemetryBatch.model_validate({"events": [EVENT] * (MAX_BATCH_EVENTS + 1)}).events) == MAX_BATCH_EVENTS + 1


def test_batch_ignores_keys_next_to_events():
    batch = TelemetryBatch.model_validate({"events": [EVENT], "sentAt": "2026-11-19T10:15:40.000Z"})
    assert batch.model_dump() == {"events": [EVENT]}


@pytest.mark.parametrize("body", [{}, {"events": "x"}, {"events": {"0": EVENT}}, {"evento": [EVENT]}])
def test_batch_needs_a_list_of_events(body):
    with pytest.raises(ValidationError):
        TelemetryBatch.model_validate(body)
