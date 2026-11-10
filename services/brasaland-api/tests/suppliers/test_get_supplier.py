"""`GET /suppliers/{id}`: la ruta `get_supplier`."""

import pytest

from app.domains.suppliers.router import delete_supplier, get_supplier
from tests.helpers import raises_api_error


def test_gsu_f1_existing_id_returns_supplier(repository, add_supplier):
    created = add_supplier()

    assert get_supplier(created.id, repository=repository) == created


@pytest.mark.parametrize("supplier_id", [0, -1])
def test_gsu_l1_zero_or_negative_id_is_not_found(supplier_id, repository, add_supplier):
    add_supplier()

    with raises_api_error(404, "supplier_not_found"):
        get_supplier(supplier_id, repository=repository)


def test_gsu_x1_unknown_id_is_not_found(repository, add_supplier):
    add_supplier()

    with raises_api_error(404, "supplier_not_found"):
        get_supplier(99, repository=repository)


def test_gsu_x1_deleted_supplier_is_not_found(repository, add_supplier):
    created = add_supplier()
    delete_supplier(created.id, repository=repository)

    with raises_api_error(404, "supplier_not_found"):
        get_supplier(created.id, repository=repository)
