"""Endpoints del gestor de incidencias: códigos, mensajes y formato de los errores."""

import pytest
from fastapi.testclient import TestClient

from app.core.errors import INTERNAL_ERROR_MESSAGE
from app.domains.incidents.dependencies import get_incident_repository
from app.main import app

URL = "/api/v1/incidents"
VALID = {
    "title": "Freidora sin temperatura",
    "description": "La freidora 2 no pasa de 120 grados.",
    "category": "equipment_failure",
    "origin": "branch",
    "branch": "miami_doral",
}


@pytest.fixture
def api(auth_headers):
    with TestClient(app, headers=auth_headers) as test_client:
        yield test_client


def create(api, **changes):
    response = api.post(URL, json={**VALID, **changes})
    assert response.status_code == 201, response.json()
    return response.json()


def error(response):
    return response.json()["error"]


# --- POST /incidents --------------------------------------------------------------------------


def test_create_returns_201_with_generated_fields(api):
    body = create(api)
    assert body["id"] == 1
    assert body["status"] == "open"
    assert body["created_at"] == body["updated_at"]
    assert {key: body[key] for key in VALID} == VALID


@pytest.mark.parametrize("field", ["title", "description", "category", "origin", "branch"])
def test_missing_field_is_400_naming_the_field(api, field):
    data = {key: value for key, value in VALID.items() if key != field}
    response = api.post(URL, json=data)
    assert response.status_code == 400
    assert error(response)["code"] == "invalid_request"
    assert error(response)["details"] == [{"field": field, "message": "Campo obligatorio."}]


def test_blank_title_is_400_with_a_clear_message(api):
    response = api.post(URL, json={**VALID, "title": "   "})
    assert response.status_code == 400
    assert error(response)["details"] == [{"field": "title", "message": "No puede estar vacío."}]


@pytest.mark.parametrize(("field", "value"), [("category", "EQUIPMENT"), ("origin", "store"), ("branch", "paris")])
def test_value_not_allowed_is_400_listing_the_options(api, field, value):
    response = api.post(URL, json={**VALID, field: value})
    assert response.status_code == 400
    detail = error(response)["details"][0]
    assert detail["field"] == field
    assert detail["message"].startswith("Debe ser uno de estos valores:")


def test_new_incident_with_another_status_is_400(api):
    response = api.post(URL, json={**VALID, "status": "resolved"})
    assert response.status_code == 400
    assert error(response)["details"][0]["field"] == "status"


def test_system_fields_are_not_accepted(api):
    response = api.post(URL, json={**VALID, "id": 7, "created_at": "2024-01-01T00:00:00Z"})
    assert response.status_code == 400
    assert {detail["field"] for detail in error(response)["details"]} == {"id", "created_at"}


def test_body_that_is_not_json_is_400(api):
    response = api.post(URL, content="no es json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert error(response)["code"] == "invalid_request"


# --- GET /incidents y /incidents/{id} -----------------------------------------------------------


def test_list_is_empty_with_an_empty_database(api):
    response = api.get(URL)
    assert response.status_code == 200
    assert response.json() == []


def test_list_filters_by_status_origin_branch_and_category(api):
    create(api)
    create(api, origin="internal", branch="central", category="pos_system")
    api.patch(f"{URL}/1/status", json={"status": "in_progress"})

    def ids(**params):
        return [incident["id"] for incident in api.get(URL, params=params).json()]

    assert ids() == [2, 1]
    assert ids(status="in_progress") == [1]
    assert ids(origin="internal") == [2]
    assert ids(branch="miami_doral") == [1]
    assert ids(category="pos_system") == [2]
    assert ids(origin="internal", branch="miami_doral") == []


def test_invalid_filter_is_400(api):
    response = api.get(URL, params={"status": "closed"})
    assert response.status_code == 400
    assert error(response)["details"][0]["field"] == "status"


def test_get_returns_the_incident(api):
    created = create(api)
    assert api.get(f"{URL}/1").json() == created


def test_get_missing_is_404(api):
    response = api.get(f"{URL}/42")
    assert response.status_code == 404
    assert error(response) == {"code": "incident_not_found", "message": "No existe ninguna incidencia con el ID 42."}


# --- PATCH /incidents/{id}/status -------------------------------------------------------------


def test_status_moves_along_the_lifecycle_and_only_changes_status(api):
    created = create(api)
    moved = api.patch(f"{URL}/1/status", json={"status": "in_progress"}).json()
    assert moved["status"] == "in_progress"
    assert moved["created_at"] == created["created_at"]
    assert moved["updated_at"] >= created["updated_at"]
    assert {key: moved[key] for key in VALID} == VALID
    assert api.patch(f"{URL}/1/status", json={"status": "resolved"}).json()["status"] == "resolved"


def test_skipping_a_step_is_400_with_the_allowed_states(api):
    create(api)
    response = api.patch(f"{URL}/1/status", json={"status": "resolved"})
    assert response.status_code == 400
    assert error(response) == {
        "code": "invalid_transition",
        "message": "Desde open solo se puede pasar a in_progress o discarded.",
    }
    assert api.get(f"{URL}/1").json()["status"] == "open"


@pytest.mark.parametrize("final", ["resolved", "discarded"])
def test_final_states_cannot_change(api, final):
    create(api)
    api.patch(f"{URL}/1/status", json={"status": "in_progress"})
    api.patch(f"{URL}/1/status", json={"status": final})
    response = api.patch(f"{URL}/1/status", json={"status": "open"})
    assert response.status_code == 400
    assert error(response)["message"] == f"La incidencia está en {final}, un estado final: ya no puede cambiar."


def test_status_patch_rejects_other_fields_and_unknown_states(api):
    create(api)
    assert api.patch(f"{URL}/1/status", json={"status": "in_progress", "title": "Otro"}).status_code == 400
    assert api.patch(f"{URL}/1/status", json={"status": "closed"}).status_code == 400
    assert api.patch(f"{URL}/1/status", json={}).status_code == 400


def test_status_of_missing_incident_is_404(api):
    assert api.patch(f"{URL}/9/status", json={"status": "in_progress"}).status_code == 404


# --- GET /incidents/summary -------------------------------------------------------------------


def test_summary_is_all_zeros_with_an_empty_database(api):
    body = api.get(f"{URL}/summary").json()
    assert body["total"] == 0
    assert body["by_status"] == {"open": 0, "in_progress": 0, "resolved": 0, "discarded": 0}
    assert body["by_origin"] == {"customer": 0, "branch": 0, "internal": 0}
    assert len(body["by_category"]) == 8 and set(body["by_category"].values()) == {0}
    assert len(body["by_branch"]) == 15 and set(body["by_branch"].values()) == {0}


def test_summary_counts_by_status_category_origin_and_branch(api):
    create(api)
    create(api, origin="customer", branch="central", category="customer_complaint")
    api.patch(f"{URL}/2/status", json={"status": "discarded"})

    body = api.get(f"{URL}/summary").json()
    assert body["total"] == 2
    assert (body["by_status"]["open"], body["by_status"]["discarded"]) == (1, 1)
    assert (body["by_category"]["equipment_failure"], body["by_category"]["customer_complaint"]) == (1, 1)
    assert (body["by_origin"]["branch"], body["by_origin"]["customer"]) == (1, 1)
    assert (body["by_branch"]["miami_doral"], body["by_branch"]["central"]) == (1, 1)


# --- Errores inesperados y compatibilidad ----------------------------------------------------


class BrokenRepository:
    def list(self, **_filters):
        raise RuntimeError("detalle interno /ruta/secreta.py línea 42")


def test_unexpected_error_is_500_with_a_generic_message(auth_headers):
    app.dependency_overrides[get_incident_repository] = BrokenRepository
    with TestClient(app, headers=auth_headers, raise_server_exceptions=False) as api:
        response = api.get(URL)
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": INTERNAL_ERROR_MESSAGE}}
    assert "secreta" not in response.text and "Traceback" not in response.text


def test_other_domains_keep_422_for_validation_errors(api):
    assert api.post("/api/v1/suppliers", json={}).status_code == 422


def test_csv_analyzer_routes_still_work_next_to_the_manager(client, sample_upload):
    # `client` usa un almacén del analizador propio: no deja un análisis en el global para otras pruebas.
    assert client.post(f"{URL}/analyze", files=sample_upload).status_code == 200
    assert client.get(f"{URL}/results/export").status_code == 200
    assert client.get(URL).json() == []
