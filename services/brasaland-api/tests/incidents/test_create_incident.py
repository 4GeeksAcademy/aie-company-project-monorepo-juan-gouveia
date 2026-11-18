"""`POST /incidents`: la ruta `create_incident` y las reglas de `IncidentCreate`."""

import pytest
from pydantic import ValidationError

from app.domains.incidents.models import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH, IncidentCreate, IncidentStatus
from app.domains.incidents.manager_router import create_incident, get_incident
from tests.incidents.helpers import incident_data


def create(repository, **changes):
    return create_incident(IncidentCreate(**incident_data(**changes)), repository=repository)


def rejected_fields(**changes) -> list[tuple]:
    with pytest.raises(ValidationError) as info:
        IncidentCreate(**incident_data(**changes))
    return [error["loc"][:1] for error in info.value.errors()]


# --- Camino feliz ---------------------------------------------------------------------------


def test_cin_f1_new_incident_starts_open_with_system_fields(repository):
    created = create(repository, title="  Parrilla 2 sin gas  ", description="  No enciende.  ")

    assert created.status == IncidentStatus.OPEN
    assert created.id == 1
    assert created.created_at == created.updated_at
    assert (created.title, created.description) == ("Parrilla 2 sin gas", "No enciende.")
    assert get_incident(created.id, repository=repository) == created


# --- Casos límite ---------------------------------------------------------------------------


def test_cin_l1_title_and_description_at_maximum_length_are_accepted(repository):
    created = create(repository, title="t" * MAX_TITLE_LENGTH, description="d" * MAX_DESCRIPTION_LENGTH)

    assert (len(created.title), len(created.description)) == (120, 2000)


@pytest.mark.parametrize(
    ("field", "length"), [("title", MAX_TITLE_LENGTH + 1), ("description", MAX_DESCRIPTION_LENGTH + 1)]
)
def test_cin_l1_one_character_over_the_maximum_is_rejected(field, length):
    assert rejected_fields(**{field: "x" * length}) == [(field,)]


def test_cin_l2_explicit_open_status_is_accepted(repository):
    assert create(repository, status="open").status == IncidentStatus.OPEN


# --- Modos de fallo -------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["in_progress", "resolved", "discarded"])
def test_cin_x1_new_incident_cannot_start_in_another_status(status):
    assert rejected_fields(status=status) == [("status",)]


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"category": "plumbing"}, "category"),
        ({"category": "CUSTOMER_COMPLAINT"}, "category"),  # valor del sistema legacy, no del briefing
        ({"origin": "phone"}, "origin"),
        ({"branch": "medellin_poblado"}, "branch"),
        ({"title": "   "}, "title"),
        ({"id": 5}, "id"),
        ({"created_at": "2026-01-01T00:00:00Z"}, "created_at"),
    ],
    ids=["categoria", "categoria-legacy", "origen", "sede", "titulo-vacio", "id", "created_at"],
)
def test_cin_x2_values_outside_the_briefing_or_system_fields_are_rejected(changes, field):
    assert rejected_fields(**changes) == [(field,)]
