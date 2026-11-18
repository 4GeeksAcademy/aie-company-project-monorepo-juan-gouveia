"""Fixtures de la batería unitaria del gestor de incidencias (API-042).

Las pruebas llaman a las funciones de `incidents/manager_router.py` con el repositorio TinyDB
temporal que crea `tests/conftest.py` (`incident_repository`, vacío en cada prueba), sin HTTP.
El tiempo se controla con el parámetro `now` del repositorio.
"""

from datetime import datetime

import pytest

from app.domains.incidents.models import Incident, IncidentCreate, IncidentStatus
from tests.incidents.helpers import T0, incident_data


@pytest.fixture
def repository(incident_repository):
    """El repositorio temporal del gestor, con un nombre corto."""
    return incident_repository


@pytest.fixture
def add_incident(repository):
    """Guarda una incidencia en el repositorio (por defecto en T0) y, si se pide, la lleva a `status`
    por transiciones válidas del ciclo de vida."""

    paths = {
        IncidentStatus.OPEN: [],
        IncidentStatus.IN_PROGRESS: [IncidentStatus.IN_PROGRESS],
        IncidentStatus.RESOLVED: [IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED],
        IncidentStatus.DISCARDED: [IncidentStatus.DISCARDED],
    }

    def add(status: IncidentStatus = IncidentStatus.OPEN, now: datetime = T0, **changes) -> Incident:
        incident = repository.create(IncidentCreate(**incident_data(**changes)), now=now)
        for step in paths[IncidentStatus(status)]:
            incident = repository.update_status(incident.id, step, now=now)
        return incident

    return add
