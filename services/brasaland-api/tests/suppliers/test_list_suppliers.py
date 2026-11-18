"""`GET /suppliers`: la ruta `list_suppliers` y sus filtros."""

import pytest

from app.domains.suppliers.models import Category, Country
from app.domains.suppliers.router import list_suppliers


def names(suppliers) -> list[str]:
    return [supplier.name for supplier in suppliers]


@pytest.fixture
def directory(add_supplier):
    """Tres proveedores: carne en Colombia, carne y bebidas en USA, y packaging en USA."""
    add_supplier(name="Carnes del Valle")
    add_supplier(name="Miami Meats", country="USA", currency="USD", rate_per_unit=4.2, categories=["carne", "bebidas"])
    add_supplier(name="Box Florida", country="USA", currency="USD", rate_per_unit=0.3, categories=["packaging"])


def test_lsu_f1_without_filters_returns_all_ordered_by_id(repository, directory):
    suppliers = list_suppliers(country=None, category=None, repository=repository)

    assert [supplier.id for supplier in suppliers] == [1, 2, 3]


def test_lsu_l1_combined_filters_return_only_suppliers_matching_both(repository, directory):
    suppliers = list_suppliers(country=Country.USA, category=Category.CARNE, repository=repository)

    assert names(suppliers) == ["Miami Meats"]


def test_lsu_l1_supplier_with_several_categories_appears_under_each(repository, directory):
    by_meat = list_suppliers(country=None, category=Category.CARNE, repository=repository)
    by_drinks = list_suppliers(country=None, category=Category.BEBIDAS, repository=repository)

    assert names(by_meat) == ["Carnes del Valle", "Miami Meats"]
    assert names(by_drinks) == ["Miami Meats"]


def test_lsu_l1_filter_without_matches_returns_empty_list(repository, directory):
    assert list_suppliers(country=Country.COLOMBIA, category=Category.PACKAGING, repository=repository) == []


def test_lsu_l1_empty_database_returns_empty_list(repository):
    assert list_suppliers(country=None, category=None, repository=repository) == []


@pytest.mark.parametrize(("enum", "value"), [(Country, "México"), (Country, "colombia"), (Category, "pescado")])
def test_lsu_x1_filter_values_outside_the_briefing_are_rejected(enum, value):
    # FastAPI valida el parámetro con estos enums: un valor que no esté en el briefing no llega a la ruta.
    with pytest.raises(ValueError):
        enum(value)
