"""Endpoints /api/v1/suppliers: respuestas, filtros y códigos HTTP (200/201, 404, 409, 422)."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app

BASE = "/api/v1/suppliers"


@pytest.fixture
def api(supplier_repository, auth_headers):
    """Cliente con la base temporal de conftest; el arranque la siembra con los 15 del briefing.

    Envía el token de un usuario autenticado: las rutas de proveedores lo exigen (AUTH-01).
    """
    with TestClient(app, headers=auth_headers) as client:
        yield client


def new_payload(**changes):
    payload = {
        "name": "Lácteos del Sur",
        "country": "Colombia",
        "categories": ["lacteos"],
        "rate_per_unit": 5200.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "pedidos@lacteosdelsur.co",
        "notes": "Pendiente de homologación.",
    }
    payload.update(changes)
    return payload


def assert_error(response, status_code: int, code: str):
    assert response.status_code == status_code
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    return error


# --- POST /suppliers ----------------------------------------------------------------------


def test_create_returns_201_with_full_object_and_id(api):
    response = api.post(BASE, json=new_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 16
    assert {key: body[key] for key in new_payload()} == new_payload()
    assert datetime.fromisoformat(body["updated_at"]).tzinfo is not None
    assert api.get(f"{BASE}/16").json() == body


def test_create_without_optional_fields(api):
    payload = new_payload()
    del payload["contact_email"], payload["notes"]
    body = api.post(BASE, json=payload).json()
    assert body["contact_email"] is None and body["notes"] is None


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"status": "deleted"}, "status"),
        ({"rate_per_unit": 0}, "rate_per_unit"),
        ({"rate_per_unit": -10}, "rate_per_unit"),
        ({"country": "Mexico"}, "country"),
        ({"currency": "USD"}, "currency"),
        ({"categories": []}, "categories"),
        ({"categories": ["carnes"]}, "categories.0"),
        ({"updated_at": "2026-11-03T10:00:00Z"}, "updated_at"),
        ({"id": 99}, "id"),
    ],
)
def test_create_rejects_invalid_input_with_422_and_writes_nothing(api, supplier_repository, changes, field):
    response = api.post(BASE, json=new_payload(**changes))

    error = assert_error(response, 422, "invalid_request")
    assert field in [item["field"] for item in error["details"]]
    assert supplier_repository.count() == 15


def test_create_rejects_missing_country(api):
    payload = new_payload()
    del payload["country"]
    error = assert_error(api.post(BASE, json=payload), 422, "invalid_request")
    assert error["details"] == [{"field": "country", "message": "Campo obligatorio."}]


def test_create_rejects_invalid_json(api):
    response = api.post(BASE, content="{no es json", headers={"content-type": "application/json"})
    assert_error(response, 422, "invalid_request")


def test_create_rejects_duplicate_name_with_409(api, supplier_repository):
    response = api.post(BASE, json=new_payload(name="carnes del valle s.a.s."))
    error = assert_error(response, 409, "duplicate_supplier")
    assert "carnes del valle" in error["message"]
    assert supplier_repository.count() == 15


# --- GET /suppliers -----------------------------------------------------------------------


def test_list_without_parameters_returns_all(api):
    response = api.get(BASE)
    assert response.status_code == 200
    suppliers = response.json()
    assert len(suppliers) == 15
    assert [supplier["id"] for supplier in suppliers] == list(range(1, 16))


@pytest.mark.parametrize(("country", "count"), [("Colombia", 9), ("USA", 6)])
def test_list_filters_by_country(api, country, count):
    suppliers = api.get(BASE, params={"country": country}).json()
    assert len(suppliers) == count
    assert {supplier["country"] for supplier in suppliers} == {country}


def test_list_filters_by_category(api):
    suppliers = api.get(BASE, params={"category": "carne"}).json()
    assert [supplier["name"] for supplier in suppliers] == [
        "Carnes del Valle S.A.S.",
        "Frigorífico Antioqueño",
        "Miami Meat Distributors LLC",
    ]
    assert all("carne" in supplier["categories"] for supplier in suppliers)


def test_list_combines_country_and_category(api):
    # "¿Qué proveedores de carne tenemos en USA?"
    suppliers = api.get(BASE, params={"country": "USA", "category": "carne"}).json()
    assert [supplier["name"] for supplier in suppliers] == ["Miami Meat Distributors LLC"]


def test_list_with_no_matches_returns_empty_list(api):
    response = api.get(BASE, params={"country": "USA", "category": "lacteos"})
    assert response.status_code == 200 and response.json() == []


@pytest.mark.parametrize("params", [{"country": "Mexico"}, {"country": "usa"}, {"category": "carnes"}])
def test_list_rejects_unknown_filter_values(api, params):
    error = assert_error(api.get(BASE, params=params), 422, "invalid_request")
    assert error["details"][0]["field"] == next(iter(params))


# --- GET /suppliers/{id} ------------------------------------------------------------------


def test_get_returns_supplier(api):
    response = api.get(f"{BASE}/9")
    assert response.status_code == 200
    assert response.json()["name"] == "Miami Meat Distributors LLC"


@pytest.mark.parametrize("supplier_id", [999, 0, -1])
def test_get_returns_404_for_missing_ids(api, supplier_id):
    error = assert_error(api.get(f"{BASE}/{supplier_id}"), 404, "supplier_not_found")
    assert str(supplier_id) in error["message"]


def test_non_numeric_id_is_422(api):
    assert_error(api.get(f"{BASE}/abc"), 422, "invalid_request")


# --- PATCH /suppliers/{id}/rate -----------------------------------------------------------


def test_update_rate_changes_rate_and_records_timestamp(api):
    before = api.get(f"{BASE}/1").json()
    response = api.patch(f"{BASE}/1/rate", json={"rate_per_unit": 29900})

    assert response.status_code == 200
    body = response.json()
    assert body["rate_per_unit"] == 29900.0
    assert datetime.fromisoformat(body["updated_at"]) > datetime.fromisoformat(before["updated_at"])
    assert {key: body[key] for key in body if key not in ("rate_per_unit", "updated_at")} == {
        key: before[key] for key in before if key not in ("rate_per_unit", "updated_at")
    }


@pytest.mark.parametrize("body", [{"rate_per_unit": 0}, {"rate_per_unit": -5}, {"rate_per_unit": "29900"}, {}])
def test_update_rate_rejects_invalid_rates(api, body):
    before = api.get(f"{BASE}/1").json()
    assert_error(api.patch(f"{BASE}/1/rate", json=body), 422, "invalid_request")
    assert api.get(f"{BASE}/1").json() == before


def test_update_rate_rejects_client_timestamp(api):
    body = {"rate_per_unit": 29900, "updated_at": "2020-01-01T00:00:00Z"}
    error = assert_error(api.patch(f"{BASE}/1/rate", json=body), 422, "invalid_request")
    assert error["details"][0]["field"] == "updated_at"


def test_update_rate_returns_404_for_missing_id(api):
    assert_error(api.patch(f"{BASE}/999/rate", json={"rate_per_unit": 10}), 404, "supplier_not_found")


# --- PATCH /suppliers/{id}/status ---------------------------------------------------------


def test_update_status_suspends_and_activates_without_touching_updated_at(api):
    before = api.get(f"{BASE}/1").json()

    suspended = api.patch(f"{BASE}/1/status", json={"status": "suspended"})
    assert suspended.status_code == 200 and suspended.json()["status"] == "suspended"
    assert suspended.json()["updated_at"] == before["updated_at"]

    activated = api.patch(f"{BASE}/1/status", json={"status": "active"})
    assert activated.json()["status"] == "active"


@pytest.mark.parametrize("value", ["inactive", "Active", "deleted", "", None])
def test_update_status_rejects_values_outside_briefing(api, value):
    error = assert_error(api.patch(f"{BASE}/1/status", json={"status": value}), 422, "invalid_request")
    assert error["details"][0]["field"] == "status"
    assert api.get(f"{BASE}/1").json()["status"] == "active"


def test_update_status_returns_404_for_missing_id(api):
    assert_error(api.patch(f"{BASE}/999/status", json={"status": "active"}), 404, "supplier_not_found")


# --- DELETE /suppliers/{id} ---------------------------------------------------------------


def test_delete_returns_deleted_supplier_and_removes_it(api):
    response = api.delete(f"{BASE}/7")
    assert response.status_code == 200
    assert response.json()["name"] == "Limpiahogar Profesional"
    assert_error(api.get(f"{BASE}/7"), 404, "supplier_not_found")
    assert len(api.get(BASE).json()) == 14


def test_delete_returns_404_for_missing_id(api):
    assert_error(api.delete(f"{BASE}/999"), 404, "supplier_not_found")


# --- Persistencia a través de la API ------------------------------------------------------


def test_changes_survive_an_api_restart(tmp_path, auth_headers):
    from app.domains.suppliers.dependencies import get_repository
    from app.domains.suppliers.repository import SupplierRepository

    path = tmp_path / "restart.json"

    first = SupplierRepository.from_path(path)
    app.dependency_overrides[get_repository] = lambda: first
    with TestClient(app, headers=auth_headers) as client:
        client.patch(f"{BASE}/2/rate", json={"rate_per_unit": 28100})
        client.post(BASE, json=new_payload())
    first.close()

    second = SupplierRepository.from_path(path)
    app.dependency_overrides[get_repository] = lambda: second
    try:
        with TestClient(app, headers=auth_headers) as client:
            suppliers = client.get(BASE).json()
        assert len(suppliers) == 16
        assert suppliers[1]["rate_per_unit"] == 28100.0
    finally:
        second.close()
