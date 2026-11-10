"""`DELETE /suppliers/{id}`: la ruta `delete_supplier`."""

from app.domains.suppliers.models import SupplierCreate
from app.domains.suppliers.router import create_supplier, delete_supplier, list_suppliers
from tests.helpers import raises_api_error
from tests.suppliers.helpers import supplier_data


def test_dsu_f1_deleted_supplier_is_returned_and_disappears(repository, add_supplier):
    kept = add_supplier(name="Carnes del Valle")
    removed = add_supplier(name="Bebidas Andinas", categories=["bebidas"])

    deleted = delete_supplier(removed.id, repository=repository)

    assert deleted == removed
    assert repository.get(removed.id) is None
    assert list_suppliers(country=None, category=None, repository=repository) == [kept]


def test_dsu_l1_name_of_deleted_supplier_can_be_used_again(repository, add_supplier):
    removed = add_supplier(name="Carnes del Valle")
    delete_supplier(removed.id, repository=repository)

    recreated = create_supplier(SupplierCreate(**supplier_data(name="carnes del valle")), repository=repository)

    assert recreated.name == "carnes del valle"


def test_dsu_x1_unknown_id_is_not_found(repository, add_supplier):
    add_supplier()

    with raises_api_error(404, "supplier_not_found"):
        delete_supplier(99, repository=repository)

    assert repository.count() == 1


def test_dsu_x1_deleting_twice_is_not_found_the_second_time(repository, add_supplier):
    created = add_supplier()
    delete_supplier(created.id, repository=repository)

    with raises_api_error(404, "supplier_not_found"):
        delete_supplier(created.id, repository=repository)
