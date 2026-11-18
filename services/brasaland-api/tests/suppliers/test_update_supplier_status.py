"""`PATCH /suppliers/{id}/status`: la ruta `update_status` y las reglas de `StatusUpdate`."""

import pytest
from pydantic import ValidationError

from app.domains.suppliers.models import StatusUpdate, SupplierStatus
from app.domains.suppliers.router import update_status
from tests.helpers import raises_api_error


def test_ssu_f1_suspending_does_not_touch_the_rate_date(repository, add_supplier, clock):
    created = add_supplier(status="active")
    clock.advance(days=1)

    updated = update_status(created.id, StatusUpdate(status=SupplierStatus.SUSPENDED), repository=repository)

    assert updated.status == SupplierStatus.SUSPENDED
    # `updated_at` es la fecha de la última tarifa, no de cualquier cambio.
    assert updated.updated_at == created.updated_at


@pytest.mark.parametrize(
    ("current", "target"),
    [("suspended", "active"), ("active", "active"), ("suspended", "suspended")],
    ids=["reactivar", "activo-otra-vez", "suspendido-otra-vez"],
)
def test_ssu_l1_reactivating_or_repeating_the_status_is_accepted(current, target, repository, add_supplier):
    created = add_supplier(status=current)

    updated = update_status(created.id, StatusUpdate(status=target), repository=repository)

    assert repository.get(created.id).status == updated.status == target


@pytest.mark.parametrize("status", ["inactive", "ACTIVE", ""])
def test_ssu_x1_status_outside_the_briefing_is_rejected(status):
    with pytest.raises(ValidationError):
        StatusUpdate(status=status)


def test_ssu_x2_unknown_id_is_not_found(repository):
    with raises_api_error(404, "supplier_not_found"):
        update_status(99, StatusUpdate(status=SupplierStatus.SUSPENDED), repository=repository)
