"""`GET /incidents/{id}`: la ruta `get_incident`."""

import pytest

from app.domains.incidents.manager_router import get_incident
from tests.helpers import raises_api_error


def test_gin_f1_existing_id_returns_incident(repository, add_incident):
    created = add_incident()

    assert get_incident(created.id, repository=repository) == created


@pytest.mark.parametrize("incident_id", [0, -1])
def test_gin_l1_zero_or_negative_id_is_not_found(incident_id, repository, add_incident):
    add_incident()

    with raises_api_error(404, "incident_not_found"):
        get_incident(incident_id, repository=repository)


def test_gin_x1_unknown_id_is_not_found(repository, add_incident):
    add_incident()

    with raises_api_error(404, "incident_not_found"):
        get_incident(99, repository=repository)
