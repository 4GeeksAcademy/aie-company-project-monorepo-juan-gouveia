"""Seeder: carga los 15 proveedores del briefing, no duplica y confirma el recuento en consola."""

from fastapi.testclient import TestClient

from app.domains.suppliers import seed as seed_module
from app.domains.suppliers.database import DB_PATH_ENV
from app.domains.suppliers.repository import SupplierRepository
from app.domains.suppliers.seed import SUPPLIERS_SEED, seed, seed_if_empty
from app.main import app


def test_seed_loads_every_briefing_supplier_exactly(supplier_repository):
    result = seed(supplier_repository)

    assert (result.inserted, result.skipped) == (15, 0)
    suppliers = supplier_repository.list()
    assert [supplier.id for supplier in suppliers] == list(range(1, 16))
    stored = [supplier.model_dump(mode="json", exclude={"id", "updated_at"}) for supplier in suppliers]
    expected = [{"contact_email": None, "notes": None, **item} for item in SUPPLIERS_SEED]
    assert stored == expected


def test_seed_counts_match_briefing(supplier_repository):
    seed(supplier_repository)
    suppliers = supplier_repository.list()
    assert sum(supplier.country == "Colombia" for supplier in suppliers) == 9
    assert sum(supplier.country == "USA" for supplier in suppliers) == 6
    assert sorted(supplier.name for supplier in suppliers if supplier.status == "suspended") == [
        "Bebidas Andinas",
        "Limpiahogar Profesional",
    ]


def test_seeded_suppliers_get_updated_at(supplier_repository):
    seed(supplier_repository)
    assert all(supplier.updated_at.tzinfo is not None for supplier in supplier_repository.list())


def test_running_seed_twice_does_not_duplicate(supplier_repository):
    seed(supplier_repository)
    second = seed(supplier_repository)

    assert (second.inserted, second.skipped) == (0, 15)
    assert supplier_repository.count() == 15


def test_seed_completes_a_partial_database(supplier_repository):
    seed(supplier_repository)
    supplier_repository.delete(3)
    supplier_repository.delete(9)

    result = seed(supplier_repository)

    assert (result.inserted, result.skipped) == (2, 13)
    names = {supplier.name for supplier in supplier_repository.list()}
    assert names == {item["name"] for item in SUPPLIERS_SEED}


def test_seed_if_empty_only_runs_on_an_empty_table(supplier_repository):
    assert seed_if_empty(supplier_repository).inserted == 15
    supplier_repository.delete(1)

    assert seed_if_empty(supplier_repository) is None
    assert supplier_repository.get(1) is None
    assert supplier_repository.count() == 14


def test_main_prints_inserted_count(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "cli.json"
    monkeypatch.setenv(DB_PATH_ENV, str(db_path))

    seed_module.main()
    first = capsys.readouterr().out
    seed_module.main()
    second = capsys.readouterr().out

    assert "15 proveedores insertados, 0 ya existían. Total en la base: 15" in first
    assert "0 proveedores insertados, 15 ya existían. Total en la base: 15" in second
    assert db_path.exists()


def test_api_startup_seeds_an_empty_database(supplier_repository):
    with TestClient(app):
        pass
    assert supplier_repository.count() == 15


def test_api_startup_does_not_reseed_a_database_with_data(supplier_repository):
    seed(supplier_repository)
    supplier_repository.delete(15)

    with TestClient(app):
        pass

    assert supplier_repository.count() == 14
    assert supplier_repository.find_by_name("Bebidas Andinas") is None
