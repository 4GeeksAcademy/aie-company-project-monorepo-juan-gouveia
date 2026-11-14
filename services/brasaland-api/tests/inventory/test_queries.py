"""Sin N+1 (decisión D5): los listados hacen un número fijo de consultas, haya las filas que haya.

Un listener de SQLAlchemy cuenta las sentencias SQL que llegan a la base. Solo las pruebas usan
SQLAlchemy directamente; el código de la API usa únicamente `sqlmodel`.
"""

import pytest
from sqlalchemy import event

from app.domains.inventory.router import get_product, list_orders, list_products


@pytest.fixture
def query_counter(inventory_engine):
    """Devuelve una función que ejecuta `action` y cuenta las sentencias SQL que lanza."""

    def count(action) -> int:
        statements = []

        def record(_conn, _cursor, statement, *_args):
            statements.append(statement)

        event.listen(inventory_engine, "before_cursor_execute", record)
        try:
            action()
        finally:
            event.remove(inventory_engine, "before_cursor_execute", record)
        return len(statements)

    return count


@pytest.fixture
def populate(add_ingredient, add_entry, add_exit):
    """Crea `size` ingredientes, cada uno con 2 entradas y 1 salida."""

    def build(size: int) -> None:
        for number in range(1, size + 1):
            add_ingredient(name=f"Ingrediente {number}", sku=f"BRS-TEST-{number:03d}")
            add_entry(ingredient_id=number, quantity=10.0)
            add_entry(ingredient_id=number, quantity=5.0)
            add_exit(ingredient_id=number, quantity=3.0)

    return build


@pytest.mark.parametrize("size", [1, 20])
def test_products_list_query_count_does_not_grow(populate, session, query_counter, size):
    populate(size)

    assert query_counter(lambda: list_products(session=session)) == 1
    assert {item.current_stock for item in list_products(session=session)} == {12.0}


@pytest.mark.parametrize("size", [1, 20])
def test_orders_list_is_two_queries_for_any_number_of_orders(populate, session, query_counter, size):
    populate(size)
    session.expunge_all()  # Sin objetos en memoria: todo lo que se lea tiene que venir de la consulta.

    orders_count = query_counter(lambda: list_orders(session=session))
    orders = list_orders(session=session)

    assert orders_count == 2
    assert (len(orders.inbound), len(orders.outbound)) == (2 * size, size)
    assert {item.ingredient.sku for item in orders.inbound} == {f"BRS-TEST-{n:03d}" for n in range(1, size + 1)}


def test_single_product_is_a_single_query(populate, session, query_counter):
    populate(3)

    assert query_counter(lambda: get_product(2, session=session)) == 1
