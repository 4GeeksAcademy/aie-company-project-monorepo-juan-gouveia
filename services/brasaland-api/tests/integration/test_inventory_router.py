"""Inventario por HTTP (Hito 5): contrato de las 6 rutas de `/api/v1/inventory`.

Comprueba lo que una prueba unitaria no ve: el registro del router bajo `/inventory`, la protección
con token, el `user_uuid` sacado del token de cada usuario, los códigos de estado, el formato
`{"error": {...}}` y que ninguna ruta permita modificar el stock directamente. La base es el SQLite
temporal de `inventory_engine`, vacío en cada prueba.
"""

import pytest

from app.domains.users.models import Role
from app.main import app
from tests.inventory.helpers import entry_data, exit_data, ingredient_data

BASE = "/api/v1/inventory"

INVENTORY_ROUTES = [
    ("get", f"{BASE}/products"),
    ("post", f"{BASE}/products"),
    ("get", f"{BASE}/products/1"),
    ("post", f"{BASE}/orders/inbound"),
    ("post", f"{BASE}/orders/outbound"),
    ("get", f"{BASE}/orders"),
]


@pytest.fixture
def headers(make_user):
    _, user_headers = make_user("operaciones@brasaland.com", role=Role.MANAGER)
    return user_headers


@pytest.fixture
def beef(api, headers):
    """Falda de ternera con 50 kg de stock (una entrada)."""
    assert api.post(f"{BASE}/products", json=ingredient_data(), headers=headers).status_code == 201
    assert api.post(f"{BASE}/orders/inbound", json=entry_data(quantity=50.0), headers=headers).status_code == 201


# --- Router y protección ---------------------------------------------------------------------


def test_router_exposes_exactly_the_six_briefing_routes_and_none_to_edit_stock():
    # Desde el esquema OpenAPI: lo que la API publica, sea cual sea su organización interna de routers.
    routes = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith(BASE)
        for method in operations
    }
    assert routes == {(method.upper(), path.replace("/1", "/{ingredient_id}")) for method, path in INVENTORY_ROUTES}


@pytest.mark.parametrize(("method", "path"), INVENTORY_ROUTES, ids=[f"{m.upper()} {p}" for m, p in INVENTORY_ROUTES])
def test_every_inventory_route_requires_a_token(api, method, path):
    response = api.request(method, path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_stock_cannot_be_modified_directly(api, headers, beef, method):
    response = api.request(method, f"{BASE}/products/1", json={"current_stock": 999}, headers=headers)

    assert response.status_code == 405
    assert api.get(f"{BASE}/products/1", headers=headers).json()["current_stock"] == 50.0


# --- Ingredientes ----------------------------------------------------------------------------


def test_created_product_starts_at_zero_and_is_listed(api, headers):
    created = api.post(f"{BASE}/products", json=ingredient_data(), headers=headers)

    assert created.status_code == 201
    assert created.json() == {**ingredient_data(), "id": 1, "current_stock": 0.0}
    assert api.get(f"{BASE}/products", headers=headers).json() == [created.json()]
    assert api.get(f"{BASE}/products/1", headers=headers).json() == created.json()


def test_product_with_current_stock_in_body_is_rejected(api, headers):
    response = api.post(f"{BASE}/products", json=ingredient_data(current_stock=100), headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "current_stock", "message": "Este campo no está permitido; lo genera el sistema o no existe."}
    ]


def test_duplicate_sku_is_409(api, headers, beef):
    response = api.post(f"{BASE}/products", json=ingredient_data(name="Otra"), headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_sku"


def test_country_filter_and_invalid_country(api, headers):
    api.post(f"{BASE}/products", json=ingredient_data(), headers=headers)
    api.post(f"{BASE}/products", json=ingredient_data(sku="BRS-PORK-001", country="US"), headers=headers)

    assert [item["sku"] for item in api.get(f"{BASE}/products?country=US", headers=headers).json()] == ["BRS-PORK-001"]
    assert api.get(f"{BASE}/products?country=Colombia", headers=headers).status_code == 422


def test_missing_product_is_404(api, headers):
    response = api.get(f"{BASE}/products/99", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ingredient_not_found"


# --- Órdenes ---------------------------------------------------------------------------------


def test_each_order_stores_the_uuid_of_the_user_who_sent_it(api, make_user, headers, beef):
    other, other_headers = make_user("cocina@brasaland.com")

    response = api.post(f"{BASE}/orders/outbound", json=exit_data(quantity=2.0), headers=other_headers)

    assert response.status_code == 201
    assert response.json()["user_uuid"] == other.id
    orders = api.get(f"{BASE}/orders", headers=headers).json()
    assert orders["outbound"][0]["user_uuid"] == other.id
    assert orders["inbound"][0]["user_uuid"] != other.id


def test_user_uuid_in_body_is_rejected(api, headers, beef):
    response = api.post(f"{BASE}/orders/inbound", json=entry_data(user_uuid="otro-usuario"), headers=headers)

    assert response.status_code == 422
    assert [item["field"] for item in response.json()["error"]["details"]] == ["user_uuid"]


def test_exit_above_stock_is_400_with_message_and_writes_nothing(api, headers, beef):
    response = api.post(f"{BASE}/orders/outbound", json=exit_data(quantity=60.0), headers=headers)

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "insufficient_stock",
            "message": "Stock insuficiente para el ingrediente 'Falda de ternera'. Disponible: 50, solicitado: 60.",
        }
    }
    assert api.get(f"{BASE}/orders", headers=headers).json()["outbound"] == []
    assert api.get(f"{BASE}/products/1", headers=headers).json()["current_stock"] == 50.0


def test_invalid_reason_is_422(api, headers, beef):
    response = api.post(f"{BASE}/orders/outbound", json=exit_data(reason="theft"), headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "reason", "message": "Debe ser uno de estos valores: 'consumption' o 'waste'."}
    ]


def test_order_of_missing_ingredient_is_404(api, headers):
    response = api.post(f"{BASE}/orders/inbound", json=entry_data(ingredient_id=99), headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ingredient_not_found"


def test_orders_list_has_ingredient_data_and_only_schema_fields(api, headers, beef):
    api.post(f"{BASE}/orders/outbound", json=exit_data(quantity=3.0, reason="waste"), headers=headers)

    orders = api.get(f"{BASE}/orders", headers=headers).json()
    entry, exit_ = orders["inbound"][0], orders["outbound"][0]
    common = {"id", "ingredient_id", "quantity", "location_id", "created_at", "user_uuid", "ingredient"}
    # Sin campos del modelo ORM (como la relación inversa `entries`): solo los del schema.
    assert set(entry) == common | {"supplier_name"}
    assert set(exit_) == common | {"reason"}
    assert entry["ingredient"] == {"id": 1, "name": "Falda de ternera", "sku": "BRS-BEEF-001", "unit": "kg", "country": "CO"}
    assert exit_["created_at"].endswith("Z")
    assert api.get(f"{BASE}/products/1", headers=headers).json()["current_stock"] == 47.0
