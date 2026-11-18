"""`GET /incidents`: la ruta `list_incidents`, su orden y sus filtros."""

from datetime import timedelta

import pytest

from app.domains.incidents.manager_router import list_incidents
from app.domains.incidents.models import Branch, IncidentCategory, IncidentOrigin, IncidentStatus
from tests.incidents.helpers import T0


def listing(repository, status=None, origin=None, branch=None, category=None):
    return list_incidents(status=status, origin=origin, branch=branch, category=category, repository=repository)


def test_lin_f1_without_filters_returns_newest_first(repository, add_incident):
    oldest = add_incident(now=T0)
    newest = add_incident(now=T0 + timedelta(hours=2))
    middle = add_incident(now=T0 + timedelta(hours=1))

    assert [incident.id for incident in listing(repository)] == [newest.id, middle.id, oldest.id]


def test_lin_l1_same_instant_is_ordered_by_descending_id(repository, add_incident):
    first = add_incident(now=T0)
    second = add_incident(now=T0)

    assert [incident.id for incident in listing(repository)] == [second.id, first.id]


def test_lin_l1_four_filters_combined_return_only_full_matches(repository, add_incident):
    match = add_incident(status="in_progress", origin="customer", branch="miami_doral", category="customer_complaint")
    add_incident(status="open", origin="customer", branch="miami_doral", category="customer_complaint")
    add_incident(status="in_progress", origin="internal", branch="miami_doral", category="customer_complaint")
    add_incident(status="in_progress", origin="customer", branch="miami_kendall", category="customer_complaint")
    add_incident(status="in_progress", origin="customer", branch="miami_doral", category="pos_system")

    found = listing(
        repository,
        status=IncidentStatus.IN_PROGRESS,
        origin=IncidentOrigin.CUSTOMER,
        branch=Branch.MIAMI_DORAL,
        category=IncidentCategory.CUSTOMER_COMPLAINT,
    )

    assert [incident.id for incident in found] == [match.id]


def test_lin_l1_empty_database_returns_empty_list(repository):
    assert listing(repository) == []


@pytest.mark.parametrize(
    ("enum", "value"),
    [(IncidentStatus, "OPEN"), (IncidentStatus, "closed"), (IncidentOrigin, "phone"), (Branch, "medellin"),
     (IncidentCategory, "CUSTOMER_COMPLAINT")],
)
def test_lin_x1_filter_values_outside_the_briefing_or_legacy_are_rejected(enum, value):
    # FastAPI valida el parámetro con estos enums: un valor legacy o inventado no llega a la ruta.
    with pytest.raises(ValueError):
        enum(value)
