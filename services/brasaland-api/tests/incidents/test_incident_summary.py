"""`GET /incidents/summary`: la ruta `incident_summary`."""

from app.domains.incidents.manager_router import incident_summary, update_incident_status
from app.domains.incidents.models import Branch, IncidentCategory, IncidentOrigin, IncidentStatus, StatusUpdate


def test_sin_f1_counts_total_and_each_dimension(repository, add_incident):
    add_incident(status="open", category="equipment_failure", origin="branch", branch="medellin_laureles")
    add_incident(status="resolved", category="customer_complaint", origin="customer", branch="medellin_laureles")
    add_incident(status="discarded", category="customer_complaint", origin="customer", branch="miami_doral")

    summary = incident_summary(repository=repository)

    assert summary.total == 3
    assert summary.by_status[IncidentStatus.OPEN] == summary.by_status[IncidentStatus.RESOLVED] == 1
    assert summary.by_status[IncidentStatus.DISCARDED] == 1
    assert summary.by_category[IncidentCategory.CUSTOMER_COMPLAINT] == 2
    assert summary.by_origin[IncidentOrigin.CUSTOMER] == 2
    assert summary.by_branch[Branch.MEDELLIN_LAURELES] == 2
    assert summary.by_branch[Branch.MIAMI_DORAL] == 1


def test_sin_l1_empty_database_has_every_briefing_value_at_zero(repository):
    summary = incident_summary(repository=repository)

    assert summary.total == 0
    # Todas las claves del briefing presentes: el panel no debe romperse por una clave ausente.
    assert summary.by_status == {status: 0 for status in IncidentStatus}
    assert summary.by_category == {category: 0 for category in IncidentCategory}
    assert summary.by_origin == {origin: 0 for origin in IncidentOrigin}
    assert summary.by_branch == {branch: 0 for branch in Branch}


def test_sin_x1_after_status_changes_each_incident_counts_once_in_its_current_status(repository, add_incident):
    first = add_incident()
    second = add_incident()
    update_incident_status(first.id, StatusUpdate(status="in_progress"), repository=repository)
    update_incident_status(first.id, StatusUpdate(status="resolved"), repository=repository)
    update_incident_status(second.id, StatusUpdate(status="discarded"), repository=repository)

    summary = incident_summary(repository=repository)

    assert summary.total == 2
    assert summary.by_status == {
        IncidentStatus.OPEN: 0,
        IncidentStatus.IN_PROGRESS: 0,
        IncidentStatus.RESOLVED: 1,
        IncidentStatus.DISCARDED: 1,
    }
