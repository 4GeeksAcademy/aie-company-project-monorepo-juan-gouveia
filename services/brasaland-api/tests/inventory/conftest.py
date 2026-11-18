"""Fixtures de la batería unitaria del inventario.

Las pruebas llaman a las funciones de `inventory/router.py` con una sesión sobre el SQLite temporal
de `tests/conftest.py` (`inventory_engine`, vacío en cada prueba), sin HTTP.
"""

import pytest
from sqlmodel import Session

from app.domains.inventory.router import create_inbound_order, create_outbound_order, create_product
from app.domains.inventory.schemas import IngredientCreate, IngredientEntryCreate, IngredientExitCreate
from app.domains.users.models import Role
from tests.inventory.helpers import entry_data, exit_data, ingredient_data


@pytest.fixture
def session(inventory_engine):
    """Sesión SQLModel sobre la base temporal, como la que abre `get_db` en cada petición."""
    with Session(inventory_engine) as db_session:
        yield db_session


@pytest.fixture
def user(make_user):
    """Usuario autenticado de TinyDB que registra las órdenes."""
    created, _ = make_user("operaciones@brasaland.com", role=Role.MANAGER)
    return created


@pytest.fixture
def add_ingredient(session):
    def add(**changes):
        return create_product(IngredientCreate(**ingredient_data(**changes)), session=session)

    return add


@pytest.fixture
def add_entry(session, user):
    def add(**changes):
        return create_inbound_order(IngredientEntryCreate(**entry_data(**changes)), current_user=user, session=session)

    return add


@pytest.fixture
def add_exit(session, user):
    def add(**changes):
        return create_outbound_order(IngredientExitCreate(**exit_data(**changes)), current_user=user, session=session)

    return add
