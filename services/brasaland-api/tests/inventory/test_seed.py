"""Semilla del inventario (`uv run seed-inventory`): datos del briefing, stock resultante e idempotencia."""

from sqlmodel import func, select

from app.domains.inventory import seed as seed_module
from app.domains.inventory.models import Ingredient, IngredientEntry, IngredientExit
from app.domains.inventory.router import list_orders, list_products
from app.domains.inventory.seed import find_seed_user_uuid, main, seed
from app.domains.users.models import Role, UserUpdate
from app.domains.users import service as user_service
from tests.inventory.helpers import USER_UUID

EXPECTED_STOCK = {
    "BRS-BEEF-001": 52.0,
    "BRS-PORK-001": 32.0,
    "BRS-SAUCE-001": 20.0,
    "BRS-SAUCE-002": 0.0,
    "BRS-PROD-001": 0.0,
    "BRS-PKG-001": 0.0,
}


def count(session, model) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


# --- seed() ----------------------------------------------------------------------------------


def test_seed_loads_the_briefing_ingredients_and_net_stock(session):
    result = seed(session, USER_UUID)

    assert (result.ingredients, result.entries, result.exits) == (6, 4, 3)
    products = list_products(session=session)
    assert {item.sku: item.current_stock for item in products} == EXPECTED_STOCK
    assert [(item.name, item.unit, item.category, item.country) for item in products] == [
        ("Falda de ternera", "kg", "meat", "CO"),
        ("Costilla de cerdo", "kg", "meat", "US"),
        ("Chimichurri", "litro", "sauce", "CO"),
        ("Salsa BBQ de la casa", "litro", "sauce", "US"),
        ("Yuca", "kg", "produce", "CO"),
        ("Caja para llevar (M)", "unidad", "packaging", "CO"),
    ]


def test_seed_orders_meet_the_briefing_minimums(session):
    seed(session, USER_UUID)
    orders = list_orders(session=session)

    beef_entries = sorted(item.quantity for item in orders.inbound if item.ingredient.sku == "BRS-BEEF-001")
    assert beef_entries == [30.0, 50.0]
    assert len({item.ingredient.sku for item in orders.inbound}) == 3
    assert {item.supplier_name for item in orders.inbound} == {
        "Carnes del Valle S.A.", "MiamiMeat Co.", "Salsas Artesanales Ltda.",
    }
    assert "waste" in {item.reason for item in orders.outbound}
    assert {item.user_uuid for item in orders.inbound + orders.outbound} == {USER_UUID}


def test_seed_is_idempotent(session):
    seed(session, USER_UUID)

    assert seed(session, USER_UUID) is None
    assert (count(session, Ingredient), count(session, IngredientEntry), count(session, IngredientExit)) == (6, 4, 3)


# --- Usuario de las órdenes ------------------------------------------------------------------


def test_seed_user_is_the_oldest_active_admin(make_user, auth_store):
    make_user("equipo@brasaland.com")
    first_admin, _ = make_user("admin@brasaland.com", role=Role.ADMIN)
    make_user("otro-admin@brasaland.com", role=Role.ADMIN)

    assert find_seed_user_uuid(auth_store) == first_admin.id

    user_service.update_user(auth_store, first_admin.id, UserUpdate(is_active=False))
    assert find_seed_user_uuid(auth_store) != first_admin.id


def test_no_seed_user_without_active_admin(make_user, auth_store):
    make_user("equipo@brasaland.com")
    assert find_seed_user_uuid(auth_store) is None


# --- main() (uv run seed-inventory) ----------------------------------------------------------


def test_main_seeds_with_the_admin_and_reports_it(inventory_engine, session, make_user, auth_store, capsys):
    admin, _ = make_user("admin@brasaland.com", role=Role.ADMIN)

    assert main(engine=inventory_engine, store=auth_store) == 0
    assert "6 ingredientes, 4 entradas y 3 salidas" in capsys.readouterr().out
    assert {item.user_uuid for item in list_orders(session=session).inbound} == {admin.id}

    assert main(engine=inventory_engine, store=auth_store) == 0
    assert "no se insertó nada" in capsys.readouterr().out


def test_main_fails_without_admin_and_writes_nothing(inventory_engine, session, auth_store, capsys):
    assert main(engine=inventory_engine, store=auth_store) == 1
    assert "uv run create-admin" in capsys.readouterr().err
    assert count(session, Ingredient) == 0


def test_main_fails_without_database_url(make_user, auth_store, monkeypatch, capsys):
    make_user("admin@brasaland.com", role=Role.ADMIN)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    seed_module.get_engine.cache_clear()

    assert main(store=auth_store) == 1
    assert "DATABASE_URL" in capsys.readouterr().err


def test_main_reports_database_errors_without_details(make_user, auth_store, capsys):
    make_user("admin@brasaland.com", role=Role.ADMIN)

    class BrokenEngine:
        """Un motor que no conecta, como Supabase con una contraseña errónea."""

    assert main(engine=BrokenEngine(), store=auth_store) == 1
    err = capsys.readouterr().err
    assert "Revisa DATABASE_URL" in err
