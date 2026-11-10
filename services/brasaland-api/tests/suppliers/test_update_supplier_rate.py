"""`PATCH /suppliers/{id}/rate`: la ruta `update_rate` y las reglas de `RateUpdate`."""

import pytest
from pydantic import ValidationError

from app.domains.suppliers.models import RateUpdate
from app.domains.suppliers.router import update_rate
from tests.helpers import raises_api_error


def test_rsu_f1_new_rate_is_saved_with_the_time_of_the_change(repository, add_supplier, clock):
    created = add_supplier(rate_per_unit=18500.0)
    changed_at = clock.advance(days=3)

    updated = update_rate(created.id, RateUpdate(rate_per_unit=19200.0), repository=repository)

    assert (updated.rate_per_unit, updated.updated_at) == (19200.0, changed_at)
    # Solo cambian la tarifa y su fecha.
    assert updated.model_dump(exclude={"rate_per_unit", "updated_at"}) == created.model_dump(
        exclude={"rate_per_unit", "updated_at"}
    )
    assert repository.get(created.id) == updated


def test_rsu_l1_same_rate_is_accepted_and_still_records_the_change(repository, add_supplier, clock):
    created = add_supplier(rate_per_unit=18500.0)
    changed_at = clock.advance(hours=1)

    updated = update_rate(created.id, RateUpdate(rate_per_unit=18500.0), repository=repository)

    # Decisión actual: cada actualización registrada es un evento de precio, aunque el valor no cambie.
    assert updated.updated_at == changed_at


@pytest.mark.parametrize(
    "data",
    [{"rate_per_unit": 0}, {"rate_per_unit": -1.5}, {"rate_per_unit": "19200"}, {"rate_per_unit": 1.0, "currency": "USD"}],
    ids=["cero", "negativa", "texto", "campo-extra"],
)
def test_rsu_x1_invalid_rate_or_extra_field_is_rejected(data):
    with pytest.raises(ValidationError):
        RateUpdate(**data)


def test_rsu_x2_unknown_id_is_not_found_and_creates_nothing(repository):
    with raises_api_error(404, "supplier_not_found"):
        update_rate(99, RateUpdate(rate_per_unit=10.0), repository=repository)

    assert repository.count() == 0
