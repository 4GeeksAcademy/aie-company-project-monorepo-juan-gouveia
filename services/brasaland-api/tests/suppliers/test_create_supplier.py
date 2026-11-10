"""`POST /suppliers`: la ruta `create_supplier` y las reglas de `SupplierCreate`."""

import math

import pytest
from pydantic import ValidationError

from app.domains.suppliers.models import SupplierCreate
from app.domains.suppliers.router import create_supplier, get_supplier
from tests.helpers import raises_api_error
from tests.suppliers.helpers import supplier_data


def create(repository, **changes):
    return create_supplier(SupplierCreate(**supplier_data(**changes)), repository=repository)


def rejected_fields(**changes) -> list[tuple]:
    with pytest.raises(ValidationError) as info:
        SupplierCreate(**supplier_data(**changes))
    return [error["loc"][:1] for error in info.value.errors()]


# --- Camino feliz ---------------------------------------------------------------------------


def test_csu_f1_valid_supplier_is_stored_with_id_and_timestamp(repository, clock):
    created = create(repository, name="  Carnes del Valle  ", notes="  Entrega martes  ")

    assert created.id == 1
    assert created.updated_at == clock.now
    assert (created.name, created.notes) == ("Carnes del Valle", "Entrega martes")
    assert get_supplier(created.id, repository=repository) == created


# --- Casos límite ---------------------------------------------------------------------------


def test_csu_l1_minimum_rate_single_category_and_empty_notes_are_accepted(repository):
    created = create(repository, rate_per_unit=0.01, categories=["bebidas"], notes="")

    assert (created.rate_per_unit, created.categories) == (0.01, ["bebidas"])
    assert created.notes is None  # unas notas vacías se guardan como null, no como ""


@pytest.mark.parametrize("name", ["CARNES DEL VALLE", "  carnes del valle ", "Carnes Del Valle"])
def test_csu_l2_duplicate_name_in_other_case_or_spaces_is_conflict(name, repository, add_supplier):
    add_supplier()

    with raises_api_error(409, "duplicate_supplier"):
        create(repository, name=name)

    assert repository.count() == 1


# --- Modos de fallo -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("country", "currency"), [("Colombia", "USD"), ("USA", "COP")], ids=["colombia-usd", "usa-cop"]
)
def test_csu_x1_country_and_currency_must_match(country, currency):
    assert rejected_fields(country=country, currency=currency) == [("currency",)]


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"rate_per_unit": 0}, "rate_per_unit"),
        ({"rate_per_unit": -5.0}, "rate_per_unit"),
        ({"rate_per_unit": "10"}, "rate_per_unit"),  # tarifa estricta: un texto no se convierte
        ({"rate_per_unit": math.nan}, "rate_per_unit"),
        ({"rate_per_unit": math.inf}, "rate_per_unit"),
        ({"categories": ["carne", "carne"]}, "categories"),
        ({"categories": []}, "categories"),
        ({"id": 7}, "id"),
        ({"updated_at": "2026-01-01T00:00:00Z"}, "updated_at"),
    ],
    ids=["tarifa-0", "tarifa-negativa", "tarifa-texto", "tarifa-nan", "tarifa-infinita",
         "categorias-repetidas", "sin-categorias", "id", "updated_at"],
)
def test_csu_x2_invalid_rate_categories_or_system_fields_are_rejected(changes, field):
    assert rejected_fields(**changes) == [(field,)]
