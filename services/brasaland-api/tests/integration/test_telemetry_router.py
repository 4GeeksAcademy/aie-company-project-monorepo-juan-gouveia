"""Receptor provisional de telemetría: `POST /telemetry/events` (fase de captura)."""

import json
import logging
from copy import deepcopy
from uuid import uuid4

import pytest

from app.domains.telemetry.router import MAX_BODY_BYTES
from tests.telemetry.helpers import EVENT

URL = "/telemetry/events"
BACKOFFICE = "http://localhost:3001"


def event(event_type: str = "page_viewed") -> dict:
    data = deepcopy(EVENT)
    data["eventId"] = str(uuid4())
    data["event_type"] = event_type
    return data


def telemetry_lines(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "api.telemetry"]


def test_accepts_a_batch_and_answers_how_many_events_arrived(api):
    response = api.post(URL, json={"events": [event(), event("login_failed"), event()]})

    assert response.status_code == 200
    assert response.json() == {"received": 3}


def test_is_public_and_outside_api_v1(api):
    assert api.post(URL, json={"events": [event()]}).status_code == 200
    assert api.post("/api/v1/telemetry/events", json={"events": [event()]}).status_code == 404


def test_logs_the_count_and_the_event_type_of_each_event(api, caplog):
    caplog.set_level(logging.INFO, logger="api.telemetry")

    api.post(URL, json={"events": [event("page_viewed"), event("login_failed"), event("page_viewed")]})

    assert telemetry_lines(caplog) == ["Lote de telemetría recibido: 3 eventos | page_viewed, login_failed, page_viewed"]


def test_accepts_the_text_plain_body_of_send_beacon(api):
    body = json.dumps({"events": [event(), event()]})

    response = api.post(URL, content=body, headers={"Content-Type": "text/plain;charset=UTF-8"})

    assert response.status_code == 200
    assert response.json() == {"received": 2}


def test_text_plain_body_is_validated_like_json(api):
    response = api.post(URL, content=json.dumps({"events": []}), headers={"Content-Type": "text/plain"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_does_not_write_anything(api, tmp_path):
    # Stub: no hay almacenamiento. La prueba se limita a que no aparezca ningún archivo nuevo en la
    # carpeta temporal de las bases de las pruebas.
    before = set(tmp_path.iterdir())
    api.post(URL, json={"events": [event()]})
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"events": []}, "events"),
        ({}, "events"),
        ({"events": [{**EVENT, "email": "ana@brasaland.com"}]}, "events.0.email"),
        ({"events": [{**EVENT, "timestamp": "2026-11-19T10:15:30Z"}]}, "events.0.timestamp"),
        ({"events": [{key: value for key, value in EVENT.items() if key != "requestId"}]}, "events.0.requestId"),
    ],
)
def test_rejects_batches_that_do_not_follow_the_envelope(api, body, field):
    response = api.post(URL, json=body)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert field in {detail["field"] for detail in error["details"]}


def test_rejects_a_batch_with_more_than_100_events(api):
    response = api.post(URL, json={"events": [event() for _ in range(101)]})

    assert response.status_code == 422


def test_rejects_a_body_that_is_not_json(api):
    response = api.post(URL, content="eventos", headers={"Content-Type": "text/plain"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_rejects_an_oversized_body_with_413(api):
    body = json.dumps({"events": [event()], "padding": "x" * MAX_BODY_BYTES})

    response = api.post(URL, content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "batch_too_large"


def test_only_accepts_post(api):
    assert api.get(URL).status_code == 405


# --- CORS: solo el origen del backoffice y solo en /telemetry ---------------------------------------


def preflight(api, path: str, origin: str):
    return api.options(
        path,
        headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
    )


def test_preflight_from_the_backoffice_is_allowed(api):
    response = preflight(api, URL, BACKOFFICE)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == BACKOFFICE
    assert "POST" in response.headers["access-control-allow-methods"]


def test_preflight_from_another_origin_is_rejected(api):
    response = preflight(api, URL, "https://otro-sitio.example")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_simple_post_from_the_backoffice_carries_the_cors_header(api):
    response = api.post(URL, json={"events": [event()]}, headers={"Origin": BACKOFFICE})

    assert response.headers["access-control-allow-origin"] == BACKOFFICE


def test_the_rest_of_the_api_has_no_cors(api):
    response = preflight(api, "/api/v1/auth/login", BACKOFFICE)

    assert "access-control-allow-origin" not in response.headers
    response = api.get("/health", headers={"Origin": BACKOFFICE})
    assert "access-control-allow-origin" not in response.headers
