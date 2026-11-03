"""Repositorio TinyDB: filtros, nombres únicos, timestamp de tarifa y persistencia en disco."""

import json
from datetime import datetime, timezone

import pytest

from app.domains.suppliers.exceptions import DuplicateSupplierError
from app.domains.suppliers.models import SupplierCreate
from app.domains.suppliers.repository import SupplierRepository
from app.domains.suppliers.seed import seed


def new_supplier(**changes) -> SupplierCreate:
    payload = {
        "name": "Proveedor Nuevo",
        "country": "USA",
        "categories": ["lacteos"],
        "rate_per_unit": 3.2,
        "currency": "USD",
        "status": "active",
    }
    payload.update(changes)
    return SupplierCreate(**payload)


@pytest.fixture
def seeded(supplier_repository):
    seed(supplier_repository)
    return supplier_repository


def test_filter_by_country(seeded):
    usa = seeded.list(country="USA")
    assert len(usa) == 6 and {supplier.country for supplier in usa} == {"USA"}


def test_filter_by_category_includes_multi_category_suppliers(seeded):
    names = [supplier.name for supplier in seeded.list(category="bebidas")]
    assert names == ["Distribuidora RefriCol", "Latin Flavors Inc.", "Bebidas Andinas"]


def test_filters_combine(seeded):
    assert [supplier.name for supplier in seeded.list(country="USA", category="carne")] == [
        "Miami Meat Distributors LLC"
    ]
    assert seeded.list(country="USA", category="lacteos") == []


def test_create_assigns_next_id_and_timestamp(seeded):
    before = datetime.now(timezone.utc)
    supplier = seeded.create(new_supplier())
    assert supplier.id == 16
    assert supplier.updated_at >= before


def test_create_rejects_duplicate_name_ignoring_case_and_spaces(seeded):
    with pytest.raises(DuplicateSupplierError):
        seeded.create(new_supplier(name="  carboco ", country="Colombia", currency="COP"))
    assert seeded.count() == 15


def test_update_rate_records_timestamp(seeded):
    original = seeded.get(1)
    updated = seeded.update_rate(1, 29900.0)
    assert updated.rate_per_unit == 29900.0
    assert updated.updated_at > original.updated_at


def test_update_status_keeps_rate_timestamp(seeded):
    original = seeded.get(1)
    updated = seeded.update_status(1, "suspended")
    assert updated.status == "suspended"
    assert updated.updated_at == original.updated_at


def test_missing_ids_return_none(seeded):
    assert seeded.get(999) is None
    assert seeded.update_rate(999, 1.0) is None
    assert seeded.update_status(999, "active") is None
    assert seeded.delete(999) is None


def test_delete_returns_supplier_and_ids_are_not_reused_while_higher_ids_exist(seeded):
    deleted = seeded.delete(5)
    assert deleted.name == "Distribuidora RefriCol"
    assert seeded.get(5) is None
    assert seeded.create(new_supplier()).id == 16


def test_data_persists_after_reopening_the_file(tmp_path):
    path = tmp_path / "persist.json"
    first = SupplierRepository.from_path(path)
    seed(first)
    first.update_rate(9, 7.1)
    first.update_status(2, "suspended")
    first.close()

    reopened = SupplierRepository.from_path(path)
    try:
        assert reopened.count() == 15
        assert reopened.get(9).rate_per_unit == 7.1
        assert reopened.get(2).status == "suspended"
    finally:
        reopened.close()


def test_file_is_readable_utf8_json(tmp_path):
    path = tmp_path / "utf8.json"
    repository = SupplierRepository.from_path(path)
    seed(repository)
    repository.close()

    content = path.read_text(encoding="utf-8")
    assert "Frigorífico Antioqueño" in content
    assert len(json.loads(content)["suppliers"]) == 15


def test_sees_inserts_made_by_another_process(tmp_path):
    # Simula `uv run seed` con la API arrancada: dos instancias sobre el mismo archivo.
    path = tmp_path / "shared.json"
    api = SupplierRepository.from_path(path)
    other = SupplierRepository.from_path(path)
    try:
        api.create(new_supplier(name="Primero"))
        other.create(new_supplier(name="Segundo"))
        third = api.create(new_supplier(name="Tercero"))
        assert third.id == 3
        assert [supplier.name for supplier in api.list()] == ["Primero", "Segundo", "Tercero"]
    finally:
        api.close()
        other.close()
