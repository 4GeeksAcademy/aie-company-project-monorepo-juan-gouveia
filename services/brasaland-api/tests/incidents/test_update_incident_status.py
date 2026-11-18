"""`PATCH /incidents/{id}/status`: la ruta `update_incident_status` y el ciclo de vida del briefing.

open → in_progress | discarded; in_progress → resolved | discarded; resolved y discarded son finales.
"""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.domains.incidents.manager_router import update_incident_status
from app.domains.incidents.models import IncidentStatus, StatusUpdate
from tests.helpers import raises_api_error
from tests.incidents.helpers import T0


def change(repository, incident_id, status):
    return update_incident_status(incident_id, StatusUpdate(status=status), repository=repository)


# --- Camino feliz ---------------------------------------------------------------------------


def test_uin_f1_open_to_in_progress_to_resolved_updates_only_status_and_updated_at(repository, add_incident):
    created = add_incident(now=T0)

    in_progress = change(repository, created.id, "in_progress")
    resolved = change(repository, created.id, "resolved")

    assert (in_progress.status, resolved.status) == (IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED)
    assert resolved.created_at == created.created_at == T0
    assert resolved.updated_at > T0  # la ruta usa la hora real: siempre posterior a T0
    assert resolved.model_dump(include={"title", "description", "category", "origin", "branch"}) == created.model_dump(
        include={"title", "description", "category", "origin", "branch"}
    )


def test_uin_f1_updated_at_is_the_time_of_the_change(repository, add_incident):
    created = add_incident(now=T0)
    later = T0 + timedelta(hours=3)

    # La ruta no recibe la hora; el repositorio sí (`now`), y es quien la guarda.
    updated = repository.update_status(created.id, IncidentStatus.IN_PROGRESS, now=later)

    assert (updated.created_at, updated.updated_at) == (T0, later)


# --- Casos límite ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "target"),
    [("open", "in_progress"), ("open", "discarded"), ("in_progress", "resolved"), ("in_progress", "discarded")],
)
def test_uin_l1_every_allowed_transition_is_accepted(current, target, repository, add_incident):
    created = add_incident(status=current)

    assert change(repository, created.id, target).status == target
    assert repository.get(created.id).status == target


# --- Modos de fallo -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "target", "message"),
    [
        ("open", "resolved", "Desde open solo se puede pasar a in_progress o discarded."),
        ("open", "open", "Desde open solo se puede pasar a in_progress o discarded."),
        ("in_progress", "open", "Desde in_progress solo se puede pasar a resolved o discarded."),
        ("in_progress", "in_progress", "Desde in_progress solo se puede pasar a resolved o discarded."),
    ],
    ids=["saltar-a-resuelta", "mismo-estado-open", "volver-a-open", "mismo-estado-in_progress"],
)
def test_uin_x1_disallowed_transition_lists_valid_options_and_changes_nothing(
    current, target, message, repository, add_incident
):
    created = add_incident(status=current)

    with raises_api_error(400, "invalid_transition") as info:
        change(repository, created.id, target)

    assert info.value.message == message
    assert repository.get(created.id) == created


@pytest.mark.parametrize("final", ["resolved", "discarded"])
@pytest.mark.parametrize("target", ["open", "in_progress", "resolved", "discarded"])
def test_uin_x2_final_states_cannot_change(final, target, repository, add_incident):
    created = add_incident(status=final)

    with raises_api_error(400, "invalid_transition") as info:
        change(repository, created.id, target)

    assert info.value.message == f"La incidencia está en {final}, un estado final: ya no puede cambiar."
    assert repository.get(created.id).status == final


def test_uin_x3_unknown_id_is_not_found(repository):
    with raises_api_error(404, "incident_not_found"):
        change(repository, 99, "in_progress")


@pytest.mark.parametrize("status", ["closed", "OPEN", "in progress"])
def test_uin_x3_status_outside_the_briefing_is_rejected(status):
    with pytest.raises(ValidationError):
        StatusUpdate(status=status)
