"""Cada orden del inventario comprueba su local en el catálogo `locations` (Fase 0c del pipeline).

Un local solo registra ingredientes de su país: 1–9 en Colombia, 10–14 en Florida. Si no, 422
`location_country_mismatch` en el campo `location_id`, y la base no cambia.
"""

import logging

import pytest
from sqlmodel import Session

from app.domains.locations.models import LOCATIONS_METADATA, Location
from app.domains.users.models import Role
from tests.inventory.helpers import entry_data, exit_data, ingredient_data

BASE = "/api/v1/inventory"


@pytest.fixture
def headers(make_user):
    _, user_headers = make_user("operaciones@brasaland.com", role=Role.MANAGER)
    return user_headers


@pytest.fixture
def beef(api, headers):
    """Falda de ternera (Colombia) con 50 kg de stock, registrados en Medellín Centro (local 1)."""
    assert api.post(f"{BASE}/products", json=ingredient_data(), headers=headers).status_code == 201
    assert api.post(f"{BASE}/orders/inbound", json=entry_data(quantity=50.0), headers=headers).status_code == 201


def orders(api, headers) -> dict:
    return api.get(f"{BASE}/orders", headers=headers).json()


def stock(api, headers) -> float:
    return api.get(f"{BASE}/products/1", headers=headers).json()["current_stock"]


# --- Combinaciones válidas ------------------------------------------------------------------------


@pytest.mark.parametrize("location_id", [1, 9])
def test_a_colombian_location_registers_a_colombian_ingredient(api, headers, beef, location_id):
    entry = api.post(f"{BASE}/orders/inbound", json=entry_data(location_id=location_id), headers=headers)
    exit_ = api.post(f"{BASE}/orders/outbound", json=exit_data(location_id=location_id), headers=headers)

    assert (entry.status_code, exit_.status_code) == (201, 201)


@pytest.mark.parametrize("location_id", [10, 14])
def test_a_florida_location_registers_a_us_ingredient(api, headers, location_id):
    pork = ingredient_data(name="Costilla de cerdo", sku="BRS-PORK-001", country="US")
    assert api.post(f"{BASE}/products", json=pork, headers=headers).status_code == 201

    entry = api.post(
        f"{BASE}/orders/inbound",
        json=entry_data(supplier_name="MiamiMeat Co.", unit_cost=6.8, location_id=location_id),
        headers=headers,
    )

    assert entry.status_code == 201


# --- País distinto --------------------------------------------------------------------------------


def test_an_entry_of_another_country_is_rejected_on_the_location_field(api, headers, beef):
    response = api.post(f"{BASE}/orders/inbound", json=entry_data(location_id=11), headers=headers)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "location_country_mismatch"
    assert error["message"] == (
        "Miami Hialeah es un local de US y «Falda de ternera» es un ingrediente de CO. "
        "Elige un ingrediente de US u otro local."
    )
    assert error["details"] == [{"field": "location_id", "message": "Miami Hialeah solo registra ingredientes de US."}]
    assert len(orders(api, headers)["inbound"]) == 1


def test_an_exit_of_another_country_is_rejected_and_the_stock_does_not_change(api, headers, beef):
    response = api.post(f"{BASE}/orders/outbound", json=exit_data(location_id=10), headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "location_country_mismatch"
    assert stock(api, headers) == 50.0
    assert orders(api, headers)["outbound"] == []


def test_the_location_is_checked_before_the_stock(api, headers, beef):
    # Una salida imposible en un local equivocado responde por el local, que es lo que hay que corregir.
    response = api.post(f"{BASE}/orders/outbound", json=exit_data(quantity=500.0, location_id=12), headers=headers)

    assert response.json()["error"]["code"] == "location_country_mismatch"


def test_an_exit_rejected_by_the_location_frees_the_ingredient_for_the_next_one(api, headers, beef):
    assert api.post(f"{BASE}/orders/outbound", json=exit_data(location_id=10), headers=headers).status_code == 422

    assert api.post(f"{BASE}/orders/outbound", json=exit_data(location_id=2), headers=headers).status_code == 201
    assert stock(api, headers) == 45.0


# --- Catálogo incompleto o ausente ----------------------------------------------------------------


def test_a_location_missing_from_the_catalogue_is_unknown(api, headers, beef, inventory_engine):
    with Session(inventory_engine) as session:
        session.delete(session.get(Location, 5))
        session.commit()

    response = api.post(f"{BASE}/orders/inbound", json=entry_data(location_id=5), headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_location"
    assert response.json()["error"]["details"][0]["field"] == "location_id"


def test_without_the_catalogue_orders_answer_503_and_nothing_is_written(api, headers, beef, inventory_engine, caplog):
    LOCATIONS_METADATA.drop_all(inventory_engine)

    with caplog.at_level(logging.ERROR, logger="api.locations"):
        entry = api.post(f"{BASE}/orders/inbound", json=entry_data(), headers=headers)
        exit_ = api.post(f"{BASE}/orders/outbound", json=exit_data(), headers=headers)

    assert (entry.status_code, exit_.status_code) == (503, 503)
    assert entry.json()["error"]["code"] == "locations_unavailable"
    assert "004_locations.sql" in caplog.text
    assert stock(api, headers) == 50.0
