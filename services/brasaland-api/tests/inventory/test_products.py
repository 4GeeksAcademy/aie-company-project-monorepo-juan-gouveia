"""`POST /inventory/products`, `GET /inventory/products` y `GET /inventory/products/{id}`."""

from app.domains.inventory.router import get_product, list_products
from app.domains.inventory.schemas import Country, IngredientRead
from tests.helpers import raises_api_error

# --- Crear -----------------------------------------------------------------------------------


def test_new_ingredient_starts_with_zero_stock(add_ingredient):
    created = add_ingredient()

    assert isinstance(created, IngredientRead)
    assert created.model_dump() == {
        "id": 1, "name": "Falda de ternera", "sku": "BRS-BEEF-001", "unit": "kg", "category": "meat",
        "country": "CO", "current_stock": 0.0,
    }


def test_duplicate_sku_is_rejected_with_409(add_ingredient, session):
    add_ingredient()

    with raises_api_error(409, "duplicate_sku"):
        add_ingredient(name="Otra falda")
    assert len(list_products(session=session)) == 1


# --- Listar y obtener ------------------------------------------------------------------------


def test_list_is_empty_without_ingredients(session):
    assert list_products(session=session) == []


def test_stock_is_entries_minus_exits(add_ingredient, add_entry, add_exit, session):
    add_ingredient()
    add_entry(quantity=50.0)
    add_entry(quantity=30.0)
    add_exit(quantity=25.0)
    add_exit(quantity=3.0, reason="waste")

    assert get_product(1, session=session).current_stock == 52.0
    assert list_products(session=session)[0].current_stock == 52.0


def test_stock_of_each_ingredient_only_counts_its_own_orders(add_ingredient, add_entry, add_exit, session):
    add_ingredient()
    add_ingredient(name="Costilla de cerdo", sku="BRS-PORK-001", country="US")
    add_ingredient(name="Yuca", sku="BRS-PROD-001", category="produce")
    add_entry(ingredient_id=1, quantity=50.0)
    add_entry(ingredient_id=2, quantity=40.0, supplier_name="MiamiMeat Co.", location_id=10)
    add_exit(ingredient_id=2, quantity=8.0, location_id=10)

    stocks = {item.sku: item.current_stock for item in list_products(session=session)}
    assert stocks == {"BRS-BEEF-001": 50.0, "BRS-PORK-001": 32.0, "BRS-PROD-001": 0.0}


def test_stock_is_global_across_locations(add_ingredient, add_entry, add_exit, session):
    # Decisión D7: location_id se guarda, pero el stock es el neto global del ingrediente.
    add_ingredient()
    add_entry(quantity=10.0, location_id=1)
    add_exit(quantity=4.0, location_id=2)

    assert get_product(1, session=session).current_stock == 6.0


def test_list_is_ordered_by_id_and_filters_by_country(add_ingredient, session):
    add_ingredient()
    add_ingredient(name="Costilla de cerdo", sku="BRS-PORK-001", country="US")
    add_ingredient(name="Chimichurri", sku="BRS-SAUCE-001", unit="litro", category="sauce")

    assert [item.id for item in list_products(session=session)] == [1, 2, 3]
    assert [item.sku for item in list_products(country=Country.CO, session=session)] == ["BRS-BEEF-001", "BRS-SAUCE-001"]
    assert [item.sku for item in list_products(country=Country.US, session=session)] == ["BRS-PORK-001"]


def test_decimal_quantities_do_not_leave_float_noise(add_ingredient, add_entry, add_exit, session):
    add_ingredient()
    add_entry(quantity=0.1)
    add_entry(quantity=0.2)
    add_exit(quantity=0.3)

    assert get_product(1, session=session).current_stock == 0.0


def test_missing_ingredient_is_404(session):
    with raises_api_error(404, "ingredient_not_found"):
        get_product(99, session=session)
