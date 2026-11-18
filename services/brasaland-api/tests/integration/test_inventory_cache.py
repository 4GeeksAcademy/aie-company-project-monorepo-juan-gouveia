"""Caché de `GET /inventory/products` y `GET /inventory/orders` por HTTP (tarea de caching, D1).

Comprueba lo que importa del lado del cliente: que la segunda lectura sale de la caché con la misma
respuesta, que cada escritura confirmada la limpia (y una rechazada no), que la caché no salta la
autenticación, que la respuesta no depende del usuario y que el TTL es lo único que corrige una
escritura hecha fuera de la API.
"""

import pytest
from sqlmodel import Session

from app.domains.inventory import service
from app.domains.inventory.cache import ORDERS_TTL_SECONDS, PRODUCTS_TTL_SECONDS, orders_cache, products_cache
from app.domains.inventory.models import IngredientEntry, IngredientExit
from app.domains.users.models import Role
from tests.inventory.helpers import entry_data, exit_data, ingredient_data

BASE = "/api/v1/inventory"
PRODUCTS = f"{BASE}/products"
ORDERS = f"{BASE}/orders"


@pytest.fixture
def headers(make_user):
    _, user_headers = make_user("operaciones@brasaland.com", role=Role.MANAGER)
    return user_headers


@pytest.fixture
def beef(api, headers):
    """Falda de ternera (CO) con 50 kg de stock."""
    assert api.post(PRODUCTS, json=ingredient_data(), headers=headers).status_code == 201
    assert api.post(f"{BASE}/orders/inbound", json=entry_data(quantity=50.0), headers=headers).status_code == 201


def stock(api, headers) -> float:
    response = api.get(PRODUCTS, headers=headers)
    return response.json()[0]["current_stock"]


@pytest.mark.parametrize("path", [PRODUCTS, ORDERS])
def test_la_segunda_lectura_sale_de_la_cache_con_la_misma_respuesta(api, headers, beef, path):
    first = api.get(path, headers=headers)
    second = api.get(path, headers=headers)

    assert (first.status_code, second.status_code) == (200, 200)
    assert (first.headers["X-Cache"], second.headers["X-Cache"]) == ("MISS", "HIT")
    assert first.headers["content-type"] == "application/json"
    assert second.content == first.content


def test_el_json_cacheado_es_el_del_contrato(api, headers, beef, inventory_engine):
    products = api.get(PRODUCTS, headers=headers).json()
    orders = api.get(ORDERS, headers=headers).json()

    with Session(inventory_engine) as session:
        assert products == [item.model_dump(mode="json") for item in service.list_ingredients(session)]
        assert orders == service.list_orders(session).model_dump(mode="json")


def test_cada_filtro_de_pais_tiene_su_propia_entrada(api, headers, beef):
    api.post(PRODUCTS, json=ingredient_data(sku="BRS-PORK-001", name="Costilla de cerdo", country="US"), headers=headers)

    colombia = api.get(PRODUCTS, params={"country": "CO"}, headers=headers)
    usa = api.get(PRODUCTS, params={"country": "US"}, headers=headers)

    assert [item["sku"] for item in colombia.json()] == ["BRS-BEEF-001"]
    assert [item["sku"] for item in usa.json()] == ["BRS-PORK-001"]
    assert (colombia.headers["X-Cache"], usa.headers["X-Cache"]) == ("MISS", "MISS")


def test_una_entrada_limpia_las_dos_caches(api, headers, beef):
    api.get(PRODUCTS, headers=headers)
    api.get(ORDERS, headers=headers)

    api.post(f"{BASE}/orders/inbound", json=entry_data(quantity=10.0), headers=headers)

    products = api.get(PRODUCTS, headers=headers)
    orders = api.get(ORDERS, headers=headers)
    assert (products.headers["X-Cache"], orders.headers["X-Cache"]) == ("MISS", "MISS")
    assert products.json()[0]["current_stock"] == 60.0
    assert len(orders.json()["inbound"]) == 2


def test_una_salida_limpia_la_cache_y_el_stock_se_ve_al_momento(api, headers, beef):
    assert stock(api, headers) == 50.0

    api.post(f"{BASE}/orders/outbound", json=exit_data(quantity=20.0), headers=headers)

    assert stock(api, headers) == 30.0
    assert len(api.get(ORDERS, headers=headers).json()["outbound"]) == 1


def test_crear_un_ingrediente_limpia_la_cache(api, headers, beef):
    api.get(PRODUCTS, headers=headers)

    api.post(PRODUCTS, json=ingredient_data(sku="BRS-SAUCE-001", name="Chimichurri", unit="litro", category="sauce"), headers=headers)

    response = api.get(PRODUCTS, headers=headers)
    assert response.headers["X-Cache"] == "MISS"
    assert len(response.json()) == 2


def test_una_salida_rechazada_no_toca_la_cache(api, headers, beef):
    api.get(PRODUCTS, headers=headers)

    rejected = api.post(f"{BASE}/orders/outbound", json=exit_data(quantity=999.0), headers=headers)

    assert rejected.status_code == 400
    assert api.get(PRODUCTS, headers=headers).headers["X-Cache"] == "HIT"


def test_la_validacion_de_stock_no_usa_la_cache(api, headers, beef, inventory_engine):
    # El stock cacheado dice 50, pero alguien consumió 45 fuera de la API: la salida se valida con
    # la base (5 disponibles), nunca con la caché.
    assert stock(api, headers) == 50.0
    with Session(inventory_engine) as session:
        session.add(IngredientExit(ingredient_id=1, quantity=45.0, reason="consumption", location_id=1, user_uuid="x"))
        session.commit()

    response = api.post(f"{BASE}/orders/outbound", json=exit_data(quantity=10.0), headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "insufficient_stock"


def test_la_cache_no_salta_la_autenticacion(api, headers, beef):
    assert api.get(PRODUCTS, headers=headers).status_code == 200
    assert api.get(ORDERS, headers=headers).status_code == 200

    assert api.get(PRODUCTS).status_code == 401
    assert api.get(ORDERS).status_code == 401


def test_la_respuesta_no_depende_del_usuario(api, headers, beef, make_user):
    # La clave es compartida porque ningún dato de la respuesta depende de quién pregunta: otro
    # usuario recibe exactamente lo mismo que recibiría sin caché.
    _, other_headers = make_user("compras@brasaland.com")
    mine = api.get(ORDERS, headers=headers)

    theirs = api.get(ORDERS, headers=other_headers)

    assert theirs.headers["X-Cache"] == "HIT"
    assert theirs.content == mine.content


@pytest.mark.parametrize(
    ("path", "cache", "ttl"),
    [(PRODUCTS, products_cache, PRODUCTS_TTL_SECONDS), (ORDERS, orders_cache, ORDERS_TTL_SECONDS)],
    ids=["products-60s", "orders-300s"],
)
def test_una_escritura_fuera_de_la_api_solo_se_ve_al_expirar_el_ttl(
    api, headers, beef, inventory_engine, monkeypatch, path, cache, ttl
):
    now = [0.0]
    monkeypatch.setattr(cache, "_clock", lambda: now[0])
    before = api.get(path, headers=headers).content
    with Session(inventory_engine) as session:
        session.add(IngredientEntry(ingredient_id=1, quantity=5.0, supplier_name="Script", location_id=2, user_uuid="x"))
        session.commit()

    now[0] = ttl - 1
    assert api.get(path, headers=headers).content == before  # intercambio aceptado: dato desactualizado

    now[0] = ttl
    refreshed = api.get(path, headers=headers)
    assert refreshed.headers["X-Cache"] == "MISS"
    assert refreshed.content != before
