"""Modelos ORM del inventario: tablas, columnas y restricciones que aplica la base de datos.

Usan el SQLite temporal de `inventory_engine` (con las claves foráneas activadas), donde
`init_db` ya creó las tablas.
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from app.domains.inventory.models import Ingredient, IngredientEntry, IngredientExit
from tests.inventory.helpers import USER_UUID, ingredient_data


def columns(engine, table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def test_init_db_creates_exactly_the_three_inventory_tables(inventory_engine):
    assert set(inspect(inventory_engine).get_table_names()) == {
        "ingredients",
        "ingredient_entries",
        "ingredient_exits",
    }


def test_no_users_table_is_replicated(inventory_engine):
    assert not any("user" in table for table in inspect(inventory_engine).get_table_names())


def test_ingredient_has_briefing_columns_and_no_stock_column(inventory_engine):
    assert columns(inventory_engine, "ingredients") == {"id", "name", "sku", "unit", "category", "country"}


def test_order_tables_have_briefing_columns(inventory_engine):
    common = {"id", "ingredient_id", "quantity", "location_id", "created_at", "user_uuid"}
    assert columns(inventory_engine, "ingredient_entries") == common | {"supplier_name"}
    assert columns(inventory_engine, "ingredient_exits") == common | {"reason"}


@pytest.mark.parametrize("table", ["ingredient_entries", "ingredient_exits"])
def test_only_foreign_key_of_orders_is_the_ingredient(inventory_engine, table):
    # user_uuid y location_id no son FK: los usuarios viven en TinyDB y los locales van aparte.
    foreign_keys = inspect(inventory_engine).get_foreign_keys(table)
    assert [(fk["constrained_columns"], fk["referred_table"]) for fk in foreign_keys] == [
        (["ingredient_id"], "ingredients")
    ]


@pytest.mark.parametrize(
    "order",
    [
        IngredientEntry(ingredient_id=999, quantity=1.0, supplier_name="X", location_id=1, user_uuid=USER_UUID),
        IngredientExit(ingredient_id=999, quantity=1.0, reason="waste", location_id=1, user_uuid=USER_UUID),
    ],
)
def test_database_rejects_order_of_missing_ingredient(inventory_engine, order):
    with Session(inventory_engine) as session:
        session.add(order)
        with pytest.raises(IntegrityError):
            session.commit()


def test_database_rejects_duplicate_sku(inventory_engine):
    with Session(inventory_engine) as session:
        session.add(Ingredient(**ingredient_data()))
        session.commit()
        session.add(Ingredient(**ingredient_data(name="Otra falda")))
        with pytest.raises(IntegrityError):
            session.commit()


def test_ids_are_autoincremental_and_created_at_is_set(inventory_engine):
    with Session(inventory_engine) as session:
        first = Ingredient(**ingredient_data())
        second = Ingredient(**ingredient_data(sku="BRS-PORK-001"))
        session.add_all([first, second])
        session.commit()
        entry = IngredientEntry(
            ingredient_id=first.id, quantity=50.0, supplier_name="Carnes del Valle S.A.", location_id=1,
            user_uuid=USER_UUID,
        )
        session.add(entry)
        session.commit()

        assert (first.id, second.id, entry.id) == (1, 2, 1)
        assert entry.created_at is not None


def test_orm_models_are_not_response_schemas():
    # Los schemas de schemas.py son clases Pydantic independientes, no subclases de SQLModel.
    from app.domains.inventory import schemas

    for name in ("IngredientRead", "IngredientEntryRead", "IngredientExitRead", "OrdersRead"):
        assert not issubclass(getattr(schemas, name), SQLModel)
