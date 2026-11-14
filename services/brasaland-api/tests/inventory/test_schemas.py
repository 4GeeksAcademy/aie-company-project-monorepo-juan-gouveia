"""Schemas de petición y respuesta del inventario: valores del briefing y campos que no se admiten."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.domains.inventory.schemas import (
    IngredientCreate,
    IngredientEntryCreate,
    IngredientEntryRead,
    IngredientExitCreate,
)
from tests.inventory.helpers import USER_UUID, entry_data, exit_data, ingredient_data


def rejected(schema, data: dict) -> list[tuple]:
    with pytest.raises(ValidationError) as info:
        schema(**data)
    return [(error["loc"][0], error["type"]) for error in info.value.errors()]


# --- IngredientCreate ------------------------------------------------------------------------


def test_valid_ingredient_is_accepted_and_text_is_trimmed():
    ingredient = IngredientCreate(**ingredient_data(name="  Falda de ternera  ", sku=" BRS-BEEF-001 "))
    assert (ingredient.name, ingredient.sku) == ("Falda de ternera", "BRS-BEEF-001")


@pytest.mark.parametrize(
    ("field", "values"),
    [
        ("unit", ["kg", "litro", "unidad"]),
        ("category", ["meat", "produce", "sauce", "beverage", "packaging", "cleaning"]),
        ("country", ["CO", "US"]),
    ],
)
def test_every_briefing_value_is_accepted(field, values):
    for value in values:
        assert getattr(IngredientCreate(**ingredient_data(**{field: value})), field) == value


@pytest.mark.parametrize(
    ("field", "value"),
    [("unit", "kilos"), ("category", "carne"), ("category", "MEAT"), ("country", "Colombia"), ("country", "co")],
)
def test_values_outside_the_briefing_are_rejected(field, value):
    assert rejected(IngredientCreate, ingredient_data(**{field: value})) == [(field, "enum")]


@pytest.mark.parametrize("field", ["name", "sku"])
def test_blank_name_or_sku_is_rejected(field):
    assert rejected(IngredientCreate, ingredient_data(**{field: "   "})) == [(field, "string_too_short")]


@pytest.mark.parametrize("field", ["current_stock", "id"])
def test_stock_and_id_cannot_be_sent(field):
    # Un ingrediente nace siempre con stock 0: no hay forma de fijar el stock al crearlo.
    assert rejected(IngredientCreate, ingredient_data(**{field: 100})) == [(field, "extra_forbidden")]


# --- Órdenes de entrada y salida -------------------------------------------------------------


def test_valid_orders_are_accepted():
    assert IngredientEntryCreate(**entry_data()).supplier_name == "Carnes del Valle S.A."
    assert IngredientExitCreate(**exit_data(reason="waste")).reason == "waste"


def test_exit_reason_only_accepts_consumption_or_waste():
    assert rejected(IngredientExitCreate, exit_data(reason="theft")) == [("reason", "enum")]


@pytest.mark.parametrize("schema, data", [(IngredientEntryCreate, entry_data), (IngredientExitCreate, exit_data)])
@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"user_uuid": USER_UUID}, ("user_uuid", "extra_forbidden")),
        ({"created_at": "2026-11-14T10:00:00"}, ("created_at", "extra_forbidden")),
        ({"quantity": 0}, ("quantity", "greater_than")),
        ({"quantity": -3.5}, ("quantity", "greater_than")),
        ({"quantity": "10"}, ("quantity", "float_type")),
        ({"location_id": 0}, ("location_id", "greater_than_equal")),
        ({"location_id": 15}, ("location_id", "less_than_equal")),
        ({"ingredient_id": 0}, ("ingredient_id", "greater_than_equal")),
    ],
)
def test_invalid_order_fields_are_rejected(schema, data, changes, expected):
    assert rejected(schema, data(**changes)) == [expected]


@pytest.mark.parametrize("location_id", [1, 14])
def test_location_limits_are_accepted(location_id):
    assert IngredientExitCreate(**exit_data(location_id=location_id)).location_id == location_id


def test_blank_supplier_name_is_rejected():
    assert rejected(IngredientEntryCreate, entry_data(supplier_name=" ")) == [("supplier_name", "string_too_short")]


# --- Respuesta -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        (datetime(2026, 11, 14, 10, 0), datetime(2026, 11, 14, 10, 0, tzinfo=UTC)),
        (datetime(2026, 11, 14, 5, 0, tzinfo=timezone(timedelta(hours=-5))), datetime(2026, 11, 14, 10, 0, tzinfo=UTC)),
    ],
)
def test_created_at_is_returned_in_utc(stored, expected):
    entry = IngredientEntryRead(
        id=1, ingredient_id=1, quantity=50.0, supplier_name="Carnes del Valle S.A.", location_id=1,
        created_at=stored, user_uuid=USER_UUID,
        ingredient={"id": 1, "name": "Falda de ternera", "sku": "BRS-BEEF-001", "unit": "kg", "country": "CO"},
    )
    assert entry.created_at == expected
    assert entry.created_at.tzinfo == UTC
