"""Repositorio TinyDB del gestor de incidencias."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.storage import lock_for
from app.domains.incidents.exceptions import InvalidTransitionError
from app.domains.incidents.incident_repository import IncidentRepository
from app.domains.incidents.models import IncidentCreate, IncidentRecord, IncidentStatus
from app.domains.suppliers.models import SupplierCreate
from app.domains.suppliers.repository import SupplierRepository

T0 = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def new(**changes) -> IncidentCreate:
    data = {
        "title": "Freidora sin temperatura",
        "description": "La freidora 2 no pasa de 120 grados.",
        "category": "equipment_failure",
        "origin": "branch",
        "branch": "miami_doral",
    }
    return IncidentCreate(**{**data, **changes})


def record(status="resolved", **changes) -> IncidentRecord:
    return IncidentRecord(**new(**changes).model_dump(exclude={"status"}), status=status)


@pytest.fixture
def repository(tmp_path):
    repo = IncidentRepository.from_path(tmp_path / "db.json")
    yield repo
    repo.close()


def test_create_assigns_id_and_equal_timestamps(repository):
    incident = repository.create(new(), now=T0)
    assert incident.id == 1
    assert incident.status == IncidentStatus.OPEN
    assert incident.created_at == incident.updated_at == T0
    assert repository.get(1) == incident


def test_get_missing_returns_none(repository):
    assert repository.get(99) is None


def test_empty_database_reads_do_not_fail(repository):
    assert repository.list() == []
    summary = repository.summary()
    assert summary.total == 0
    assert set(summary.by_status.values()) == {0}
    assert len(summary.by_category) == 8 and len(summary.by_origin) == 3 and len(summary.by_branch) == 15


def test_list_is_newest_first_and_filters_combine(repository):
    repository.create(new(branch="central", origin="internal"), now=T0)
    repository.create(new(category="pos_system"), now=T0 + timedelta(hours=1))
    repository.create(new(), now=T0 + timedelta(hours=2))

    assert [incident.id for incident in repository.list()] == [3, 2, 1]
    assert [incident.id for incident in repository.list(branch="miami_doral", category="equipment_failure")] == [3]
    assert [incident.id for incident in repository.list(origin="internal")] == [1]
    assert repository.list(status="resolved") == []


def test_update_status_follows_the_lifecycle(repository):
    repository.create(new(), now=T0)
    moved = repository.update_status(1, IncidentStatus.IN_PROGRESS, now=T0 + timedelta(minutes=5))
    assert moved.status == IncidentStatus.IN_PROGRESS
    assert moved.created_at == T0 and moved.updated_at == T0 + timedelta(minutes=5)
    assert repository.update_status(1, IncidentStatus.RESOLVED).status == IncidentStatus.RESOLVED


@pytest.mark.parametrize(
    ("path", "target"),
    [
        ([], IncidentStatus.RESOLVED),
        ([], IncidentStatus.OPEN),
        ([IncidentStatus.IN_PROGRESS], IncidentStatus.OPEN),
        ([IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED], IncidentStatus.DISCARDED),
        ([IncidentStatus.DISCARDED], IncidentStatus.IN_PROGRESS),
    ],
)
def test_invalid_transitions_are_rejected_without_changes(repository, path, target):
    repository.create(new(), now=T0)
    for status in path:
        repository.update_status(1, status)
    before = repository.get(1)
    with pytest.raises(InvalidTransitionError):
        repository.update_status(1, target)
    assert repository.get(1) == before


def test_update_status_of_missing_incident_returns_none(repository):
    assert repository.update_status(5, IncidentStatus.IN_PROGRESS) is None


def test_summary_counts_every_breakdown(repository):
    repository.create(new())
    repository.create(new(category="supply_issue", branch="central", origin="internal"))
    repository.update_status(2, IncidentStatus.DISCARDED)

    summary = repository.summary()
    assert summary.total == 2
    assert summary.by_status[IncidentStatus.OPEN] == 1 and summary.by_status[IncidentStatus.DISCARDED] == 1
    assert summary.by_category["equipment_failure"] == 1 and summary.by_category["supply_issue"] == 1
    assert summary.by_origin["branch"] == 1 and summary.by_origin["internal"] == 1
    assert summary.by_branch["miami_doral"] == 1 and summary.by_branch["central"] == 1
    assert summary.by_branch["fort_lauderdale"] == 0


def test_seed_insert_is_idempotent_by_source_id(repository):
    created_at = datetime(2024, 1, 14, tzinfo=timezone.utc)
    incident = repository.create_from_seed("BRS-000001", record(), created_at)
    assert incident.status == IncidentStatus.RESOLVED
    assert incident.created_at == incident.updated_at == created_at
    assert repository.is_seeded("BRS-000001")

    assert repository.create_from_seed("BRS-000001", record(), created_at) is None
    assert len(repository.list()) == 1
    # Mismo título y fecha con otro incident_id: es otro registro del CSV y se inserta.
    assert repository.create_from_seed("BRS-000002", record(), created_at) is not None


def test_seed_id_is_not_stored_in_the_incident(repository, tmp_path):
    repository.create_from_seed("BRS-000001", record(), T0)
    assert "source_id" not in repository.get(1).model_dump()
    assert "BRS-000001" not in str(repository._table.all())


def test_ids_come_from_the_file_when_another_process_inserted(tmp_path):
    path = tmp_path / "db.json"
    api = IncidentRepository.from_path(path)
    api.create(new())
    script = IncidentRepository.from_path(path)
    script.create_from_seed("BRS-000001", record(), T0)
    # Sin calcular el ID desde el archivo, la API reutilizaría el 2 y fallaría.
    assert api.create(new()).id == 3
    api.close()
    script.close()


def test_suppliers_and_incidents_share_the_file_and_its_lock(tmp_path):
    path = tmp_path / "db.json"
    incidents = IncidentRepository.from_path(path)
    suppliers = SupplierRepository.from_path(path)
    assert incidents._lock is suppliers._lock is lock_for(path)

    incidents.create(new())
    suppliers.create(
        SupplierCreate(
            name="Carnes del Valle",
            country="Colombia",
            categories=["carne"],
            rate_per_unit=28500,
            currency="COP",
            status="active",
        )
    )
    incidents.create(new())
    assert len(incidents.list()) == 2 and suppliers.count() == 1
    incidents.close()
    suppliers.close()
