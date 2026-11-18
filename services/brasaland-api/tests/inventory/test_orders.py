"""`POST /inventory/orders/inbound`, `POST /inventory/orders/outbound` y `GET /inventory/orders`."""

from datetime import UTC, datetime

import pytest
from sqlmodel import func, select

from app.core.errors import ApiError
from app.domains.inventory import models
from app.domains.inventory.models import IngredientEntry, IngredientExit
from app.domains.inventory.router import get_product, list_orders
from tests.helpers import raises_api_error


def count(session, model) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


# --- Entradas --------------------------------------------------------------------------------


def test_entry_is_stored_with_the_authenticated_user(add_ingredient, add_entry, user):
    add_ingredient()
    entry = add_entry(quantity=50.0)

    assert entry.user_uuid == user.id
    assert (entry.id, entry.quantity, entry.supplier_name, entry.location_id) == (1, 50.0, "Carnes del Valle S.A.", 1)
    assert entry.ingredient.model_dump() == {
        "id": 1, "name": "Falda de ternera", "sku": "BRS-BEEF-001", "unit": "kg", "country": "CO",
    }
    assert entry.created_at.tzinfo == UTC


def test_entry_of_missing_ingredient_is_404_and_writes_nothing(add_entry, session):
    with raises_api_error(404, "ingredient_not_found"):
        add_entry(ingredient_id=99)
    assert count(session, IngredientEntry) == 0


# --- Salidas ---------------------------------------------------------------------------------


def test_exit_reduces_stock_and_keeps_reason_and_user(add_ingredient, add_entry, add_exit, user, session):
    add_ingredient()
    add_entry(quantity=50.0)
    exit_ = add_exit(quantity=3.0, reason="waste", location_id=14)

    assert (exit_.reason, exit_.location_id, exit_.user_uuid) == ("waste", 14, user.id)
    assert get_product(1, session=session).current_stock == 47.0


def test_exit_can_leave_stock_exactly_at_zero(add_ingredient, add_entry, add_exit, session):
    add_ingredient()
    add_entry(quantity=12.5)
    add_exit(quantity=12.5)

    assert get_product(1, session=session).current_stock == 0.0


def test_exit_above_stock_is_rejected_before_writing(add_ingredient, add_entry, add_exit, session):
    add_ingredient()
    add_entry(quantity=50.0)
    add_exit(quantity=10.0)

    with raises_api_error(400, "insufficient_stock") as info:
        add_exit(quantity=40.5)

    assert info.value.message == (
        "Stock insuficiente para el ingrediente 'Falda de ternera'. Disponible: 40, solicitado: 40.5."
    )
    assert count(session, IngredientExit) == 1
    assert get_product(1, session=session).current_stock == 40.0


def test_exit_of_ingredient_without_entries_is_rejected(add_ingredient, add_exit, session):
    add_ingredient()

    with raises_api_error(400, "insufficient_stock") as info:
        add_exit(quantity=1.0)
    assert "Disponible: 0, solicitado: 1." in info.value.message
    assert count(session, IngredientExit) == 0


def test_exit_of_missing_ingredient_is_404(add_exit, session):
    with raises_api_error(404, "ingredient_not_found"):
        add_exit(ingredient_id=99)
    assert count(session, IngredientExit) == 0


def test_rejected_exit_does_not_block_the_next_one(add_ingredient, add_entry, add_exit, session):
    add_ingredient()
    add_entry(quantity=5.0)
    with pytest.raises(ApiError):
        add_exit(quantity=6.0)

    assert add_exit(quantity=5.0).quantity == 5.0
    assert get_product(1, session=session).current_stock == 0.0


# --- Listado ---------------------------------------------------------------------------------


def test_list_is_empty_without_orders(session):
    assert list_orders(session=session).model_dump() == {"inbound": [], "outbound": []}


def test_list_returns_entries_and_exits_newest_first_with_ingredient(
    add_ingredient, add_entry, add_exit, user, session, monkeypatch
):
    times = iter(datetime(2026, 11, 14, hour, tzinfo=UTC) for hour in range(8, 20))
    monkeypatch.setattr(models, "utc_now", lambda: next(times))
    # default_factory guarda la función al definir el modelo: se sustituye también ahí.
    for model in (IngredientEntry, IngredientExit):
        monkeypatch.setattr(model.model_fields["created_at"], "default_factory", lambda: next(times))

    add_ingredient()
    add_ingredient(name="Chimichurri", sku="BRS-SAUCE-001", unit="litro", category="sauce")
    add_entry(ingredient_id=1, quantity=50.0)
    add_entry(ingredient_id=2, quantity=20.0, supplier_name="Salsas Artesanales Ltda.")
    add_exit(ingredient_id=2, quantity=5.0)

    orders = list_orders(session=session)
    assert [(item.id, item.ingredient.sku) for item in orders.inbound] == [(2, "BRS-SAUCE-001"), (1, "BRS-BEEF-001")]
    assert [(item.id, item.ingredient.name, item.reason) for item in orders.outbound] == [
        (1, "Chimichurri", "consumption")
    ]
    assert {item.user_uuid for item in orders.inbound + orders.outbound} == {user.id}
