"""Modelo del gestor de incidencias: valores exactos del briefing, ciclo de vida y validación de entrada."""

import pytest
from pydantic import ValidationError

from app.domains.incidents.models import (
    TRANSITIONS,
    Branch,
    IncidentCategory,
    IncidentCreate,
    IncidentOrigin,
    IncidentRecord,
    IncidentStatus,
    StatusUpdate,
)

VALID = {
    "title": "Freidora sin temperatura",
    "description": "La freidora 2 no pasa de 120 grados.",
    "category": "equipment_failure",
    "origin": "branch",
    "branch": "miami_doral",
}


def values(enum):
    return [member.value for member in enum]


def test_categories_are_exactly_the_briefing_ones():
    assert values(IncidentCategory) == [
        "equipment_failure",
        "supply_issue",
        "customer_complaint",
        "staff_issue",
        "facility_issue",
        "pos_system",
        "delivery_issue",
        "other",
    ]


def test_statuses_origins_and_branches_are_exactly_the_briefing_ones():
    assert values(IncidentStatus) == ["open", "in_progress", "resolved", "discarded"]
    assert values(IncidentOrigin) == ["customer", "branch", "internal"]
    assert values(Branch) == [
        "central",
        "medellin_centro",
        "medellin_laureles",
        "medellin_envigado",
        "medellin_bello",
        "medellin_itagui",
        "bogota_chapinero",
        "bogota_usaquen",
        "cali_granada",
        "barranquilla_norte",
        "miami_doral",
        "miami_hialeah",
        "miami_kendall",
        "orlando_international",
        "fort_lauderdale",
    ]


def test_lifecycle_matches_the_briefing():
    assert {state.value: [target.value for target in targets] for state, targets in TRANSITIONS.items()} == {
        "open": ["in_progress", "discarded"],
        "in_progress": ["resolved", "discarded"],
        "resolved": [],
        "discarded": [],
    }


def test_new_incident_starts_open_and_trims_text():
    incident = IncidentCreate(**{**VALID, "title": "  Freidora  ", "description": "  No calienta  "})
    assert incident.status == IncidentStatus.OPEN
    assert (incident.title, incident.description) == ("Freidora", "No calienta")


def test_status_open_can_be_sent_explicitly():
    assert IncidentCreate(**VALID, status="open").status == IncidentStatus.OPEN


@pytest.mark.parametrize("status", ["in_progress", "resolved", "discarded"])
def test_new_incident_cannot_start_in_another_status(status):
    with pytest.raises(ValidationError, match="siempre empieza en open"):
        IncidentCreate(**VALID, status=status)


@pytest.mark.parametrize("field", ["title", "description", "category", "origin", "branch"])
def test_required_fields(field):
    data = {key: value for key, value in VALID.items() if key != field}
    with pytest.raises(ValidationError) as error:
        IncidentCreate(**data)
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("field", ["title", "description"])
def test_blank_text_is_rejected(field):
    with pytest.raises(ValidationError):
        IncidentCreate(**{**VALID, field: "   "})


def test_text_length_limits():
    IncidentCreate(**{**VALID, "title": "x" * 120, "description": "y" * 2000})
    with pytest.raises(ValidationError):
        IncidentCreate(**{**VALID, "title": "x" * 121})
    with pytest.raises(ValidationError):
        IncidentCreate(**{**VALID, "description": "y" * 2001})


@pytest.mark.parametrize(
    ("field", "value"),
    [("category", "EQUIPMENT"), ("origin", "store"), ("branch", "paris"), ("branch", "Medellín Centro")],
)
def test_values_outside_the_briefing_are_rejected(field, value):
    with pytest.raises(ValidationError):
        IncidentCreate(**{**VALID, field: value})


@pytest.mark.parametrize("field", ["id", "created_at", "updated_at", "reported_by"])
def test_system_or_unknown_fields_are_rejected(field):
    with pytest.raises(ValidationError):
        IncidentCreate(**VALID, **{field: "x"})


def test_seed_record_accepts_any_status():
    assert IncidentRecord(**VALID, status="resolved").status == IncidentStatus.RESOLVED


def test_status_update_only_accepts_status():
    assert StatusUpdate(status="in_progress").status == IncidentStatus.IN_PROGRESS
    with pytest.raises(ValidationError):
        StatusUpdate(status="in_progress", title="otro")
    with pytest.raises(ValidationError):
        StatusUpdate(status="closed")
