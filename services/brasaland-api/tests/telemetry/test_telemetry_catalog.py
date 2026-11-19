"""El catálogo de la API (`catalog.py`) es el de `docs/telemetry/event-schemas.json`, sin desfases."""

import json
import re

import pytest

from app.domains.telemetry.catalog import TELEMETRY_CATALOG
from app.domains.telemetry.generate_catalog import OUTPUT_PATH, SCHEMAS_PATH, build_catalog, render_catalog
from app.domains.telemetry.service import check_properties, parse_batch, to_row
from app.domains.telemetry.schemas import TelemetryEvent

ENVELOPE_TAGS = {"session_id", "user_id", "request_id", "schema_version", "environment"}

pytestmark = pytest.mark.skipif(not SCHEMAS_PATH.exists(), reason="docs/ no está disponible (p. ej., en la imagen de la API)")


@pytest.fixture(scope="module")
def schemas():
    return json.loads(SCHEMAS_PATH.read_text(encoding="utf-8"))


def test_the_generated_catalog_is_up_to_date(schemas):
    # Si falla: ejecuta `uv run telemetry-catalog` después de cambiar event-schemas.json.
    assert OUTPUT_PATH.read_text(encoding="utf-8") == render_catalog(build_catalog(schemas))


def test_the_catalog_has_the_44_events_of_the_plan(schemas):
    assert set(TELEMETRY_CATALOG) == set(schemas["definitions"]["events"])
    assert len(TELEMETRY_CATALOG) == 44


def test_levels_values_and_messages_only_use_keys_of_the_allowlist():
    for event_type, entry in TELEMETRY_CATALOG.items():
        assert entry.level in {"info", "warn", "error"}, event_type
        assert entry.value is None or entry.value in entry.allowed, event_type
        for hole in re.findall(r"\{(\w+)\}", entry.message):
            assert hole in entry.allowed, (event_type, hole)


def test_no_property_uses_the_names_of_the_envelope_fields_stored_in_tags():
    for event_type, entry in TELEMETRY_CATALOG.items():
        assert not ENVELOPE_TAGS & set(entry.allowed), event_type


def test_every_schema_example_is_accepted_and_mapped(schemas):
    examples = [event["examples"][0] for event in schemas["definitions"]["events"].values()]

    parsed = parse_batch(examples)

    assert parsed.rejections == []
    for raw, event in zip(examples, parsed.valid, strict=True):
        row = to_row(event)
        assert row["tags"] == {**raw["properties"], **{key: row["tags"][key] for key in ENVELOPE_TAGS}}
        assert len(row["message"]) <= 200
        holes = re.findall(r"\{(\w+)\}", TELEMETRY_CATALOG[event.event_type].message)
        assert not any(f"{{{hole}}}" in row["message"] for hole in holes), row["message"]


def test_a_numeric_value_key_points_to_a_number_in_the_examples(schemas):
    for event_type, entry in TELEMETRY_CATALOG.items():
        if entry.value is None:
            continue
        example = schemas["definitions"]["events"][event_type]["examples"][0]
        event = TelemetryEvent.model_validate(example)
        assert check_properties(event) is None
        expected = example["properties"].get(entry.value)
        assert (to_row(event)["value"] is None) == (expected is None), event_type
