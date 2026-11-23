"""Receptor de telemetría: `POST /telemetry/events` (fase de almacenamiento, plan sección 14.3).

Las pruebas usan el SQLite temporal de `tests/conftest.py`; la tabla `telemetry_events` se crea aquí,
porque `init_db` no la conoce (en Supabase la crea la migración 002).
"""

import json
import logging
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import event as sa_event
from sqlmodel import Session, select

from app.domains.telemetry.models import TELEMETRY_METADATA, TelemetryEventRow
from app.domains.telemetry.router import MAX_BODY_BYTES
from app.domains.telemetry.schemas import MAX_BATCH_EVENTS
from tests.telemetry.helpers import make_event

URL = "/telemetry/events"
BACKOFFICE = "http://localhost:3001"


@pytest.fixture(autouse=True)
def telemetry_table(inventory_engine):
    TELEMETRY_METADATA.create_all(inventory_engine)
    return inventory_engine


def stored_rows(engine) -> list[TelemetryEventRow]:
    with Session(engine) as session:
        return list(session.exec(select(TelemetryEventRow)).all())


def telemetry_lines(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "api.telemetry"]


@pytest.fixture
def insert_statements(inventory_engine):
    """Cuenta las sentencias INSERT que llegan a la base durante la prueba."""
    statements: list[str] = []

    def count(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("INSERT INTO TELEMETRY_EVENTS"):
            statements.append(statement)

    sa_event.listen(inventory_engine, "before_cursor_execute", count)
    yield statements
    sa_event.remove(inventory_engine, "before_cursor_execute", count)


# --- Lotes válidos ------------------------------------------------------------------------------------


def test_stores_a_valid_batch_and_reports_it(api, telemetry_table):
    events = [make_event("page_viewed"), make_event("inbound_order_created"), make_event("login_failed")]

    response = api.post(URL, json={"events": events})

    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 3, "rejected": 0}
    assert {str(row.id) for row in stored_rows(telemetry_table)} == {event["eventId"] for event in events}


def test_maps_each_event_to_its_row(api, telemetry_table):
    event = make_event("stock_waste_registered")

    api.post(URL, json={"events": [event]})

    [row] = stored_rows(telemetry_table)
    assert row.id == UUID(event["eventId"])
    assert row.timestamp.isoformat().startswith("2026-11-19T10:15:30.123")
    assert row.service == "backoffice"
    assert row.event_type == "stock_waste_registered"
    assert row.level == "info"
    assert row.value == Decimal("1.2")
    assert row.message == "Merma de 1.2 kg de 12 en 3 (expired)"
    assert row.tags == {
        **event["properties"],
        "session_id": event["sessionId"],
        "user_id": event["userId"],
        "request_id": event["requestId"],
        "schema_version": "1.0.0",
        "environment": "development",
    }


def test_stores_the_unit_cost_of_a_waste_event_1_1_0(api, telemetry_table):
    # stock_waste_registered 1.1.0 admite unit_cost (plan, §17); la 1.0.0 sin él sigue valiendo (arriba).
    event = make_event("stock_waste_registered", schemaVersion="1.1.0")
    event["properties"]["unit_cost"] = 38350

    response = api.post(URL, json={"events": [event]})

    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}
    [row] = stored_rows(telemetry_table)
    assert row.tags["unit_cost"] == 38350
    assert row.tags["schema_version"] == "1.1.0"


def test_technical_events_get_their_level_and_message(api, telemetry_table):
    api.post(URL, json={"events": [make_event("frontend_error_captured"), make_event("login_failed")]})

    rows = {row.event_type: row for row in stored_rows(telemetry_table)}
    assert rows["frontend_error_captured"].level == "error"
    assert rows["frontend_error_captured"].message == (
        "TypeError en /gestor-incidencias: Cannot read properties of undefined (reading 'status')"
    )
    assert rows["login_failed"].level == "warn"
    assert rows["login_failed"].value is None


def test_accepts_the_text_plain_body_of_send_beacon(api, telemetry_table):
    body = json.dumps({"events": [make_event(), make_event()]})

    response = api.post(URL, content=body, headers={"Content-Type": "text/plain;charset=UTF-8"})

    assert response.json() == {"received": 2, "stored": 2, "rejected": 0}
    assert len(stored_rows(telemetry_table)) == 2


def test_writes_the_whole_batch_with_a_single_insert(api, insert_statements):
    api.post(URL, json={"events": [make_event() for _ in range(20)]})

    assert len(insert_statements) == 1


def test_an_empty_batch_answers_zeros_without_touching_the_database(api, insert_statements):
    response = api.post(URL, json={"events": []})

    assert response.status_code == 200
    assert response.json() == {"received": 0, "stored": 0, "rejected": 0}
    assert insert_statements == []


def test_ignores_keys_next_to_events(api):
    response = api.post(URL, json={"events": [make_event()], "sentAt": "2026-11-19T10:15:40.000Z"})

    assert response.json() == {"received": 1, "stored": 1, "rejected": 0}


# --- Aceptación parcial ------------------------------------------------------------------------------


def test_rejects_invalid_events_one_by_one_and_stores_the_rest(api, telemetry_table):
    valid = [make_event("inbound_order_created"), make_event("page_viewed")]
    missing_envelope_field = {key: value for key, value in make_event().items() if key != "requestId"}
    bad_timestamp = make_event(timestamp="2026-11-19T10:15:30Z")
    extra_envelope_key = {**make_event(), "email": "ana@brasaland.com"}
    outside_allowlist = make_event("login_failed", properties={"failure_reason": "invalid_credentials", "email": "ana@brasaland.com"})
    missing_required = make_event("inbound_order_created", properties={"order_id": 1})
    unknown_type = {**make_event(), "event_type": "pizza_ordered"}

    response = api.post(
        URL,
        json={
            "events": [
                valid[0],
                missing_envelope_field,
                bad_timestamp,
                3,
                extra_envelope_key,
                outside_allowlist,
                missing_required,
                unknown_type,
                valid[1],
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"received": 9, "stored": 2, "rejected": 7}
    assert {str(row.id) for row in stored_rows(telemetry_table)} == {event["eventId"] for event in valid}


def test_answers_200_even_when_every_event_is_rejected(api, telemetry_table):
    response = api.post(URL, json={"events": [1, "x", None, {}]})

    assert response.status_code == 200
    assert response.json() == {"received": 4, "stored": 0, "rejected": 4}
    assert stored_rows(telemetry_table) == []


def test_rejects_values_postgresql_cannot_store(api, telemetry_table):
    nan = make_event("stock_waste_registered")
    nan["properties"]["quantity"] = float("nan")
    nul = make_event("page_viewed")
    nul["properties"]["route"] = "/inventario\u0000"
    body = json.dumps({"events": [nan, nul, make_event()]})  # json.dumps escribe NaN tal cual

    response = api.post(URL, content=body, headers={"Content-Type": "application/json"})

    assert response.json() == {"received": 3, "stored": 1, "rejected": 2}


# --- Repetidos ----------------------------------------------------------------------------------------


def test_a_repeated_event_does_not_create_another_row(api, telemetry_table):
    event = make_event()
    first = api.post(URL, json={"events": [event]})
    retry = api.post(URL, json={"events": [event, make_event()]})

    assert first.json() == {"received": 1, "stored": 1, "rejected": 0}
    assert retry.json() == {"received": 2, "stored": 2, "rejected": 0}
    assert len(stored_rows(telemetry_table)) == 2


def test_the_same_event_twice_in_one_batch_is_stored_once(api, telemetry_table):
    event = make_event()

    response = api.post(URL, json={"events": [event, event]})

    assert response.json() == {"received": 2, "stored": 2, "rejected": 0}
    assert len(stored_rows(telemetry_table)) == 1


# --- El lote en sí ------------------------------------------------------------------------------------


@pytest.mark.parametrize("body", [{}, {"events": "x"}, {"evento": []}, [make_event()]])
def test_a_body_without_a_list_of_events_is_a_422(api, body):
    response = api.post(URL, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_rejects_a_body_that_is_not_json(api):
    response = api.post(URL, content="eventos", headers={"Content-Type": "text/plain"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_rejects_a_batch_with_more_than_the_maximum_events(api, telemetry_table):
    response = api.post(URL, json={"events": [make_event() for _ in range(MAX_BATCH_EVENTS + 1)]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "too_many_events"
    assert stored_rows(telemetry_table) == []


def test_accepts_exactly_the_maximum(api):
    response = api.post(URL, json={"events": [make_event() for _ in range(MAX_BATCH_EVENTS)]})

    assert response.json()["stored"] == MAX_BATCH_EVENTS


def test_rejects_an_oversized_body_with_413(api):
    body = json.dumps({"events": [make_event()], "padding": "x" * MAX_BODY_BYTES})

    response = api.post(URL, content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "batch_too_large"


def test_is_public_and_outside_api_v1(api):
    assert api.post(URL, json={"events": [make_event()]}).status_code == 200
    assert api.post("/api/v1/telemetry/events", json={"events": [make_event()]}).status_code == 404


def test_only_accepts_post(api):
    assert api.get(URL).status_code == 405


# --- Fallos de la base --------------------------------------------------------------------------------


def test_without_the_table_answers_503_and_asks_for_the_migration(api, telemetry_table, caplog):
    TELEMETRY_METADATA.drop_all(telemetry_table)
    caplog.set_level(logging.INFO, logger="api.telemetry")

    response = api.post(URL, json={"events": [make_event()]})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "telemetry_storage_unavailable"
    assert any("migrations/002_telemetry_events.sql" in line for line in telemetry_lines(caplog))


def test_a_database_failure_answers_503_and_stores_nothing(api, telemetry_table, monkeypatch, caplog):
    from sqlalchemy.exc import OperationalError

    def broken(*_args, **_kwargs):
        raise OperationalError("INSERT ...", {"tags": "ana@brasaland.com"}, Exception("server closed the connection\nDETAIL: ana@brasaland.com"))

    monkeypatch.setattr(Session, "exec", broken)
    caplog.set_level(logging.INFO, logger="api.telemetry")

    response = api.post(URL, json={"events": [make_event()]})
    monkeypatch.undo()

    assert response.status_code == 503
    assert stored_rows(telemetry_table) == []
    lines = telemetry_lines(caplog)
    assert any("server closed the connection" in line for line in lines)
    assert not any("ana@brasaland.com" in line for line in lines)


# --- Log ------------------------------------------------------------------------------------------------


def test_logs_one_line_per_batch_with_counts_and_types(api, caplog):
    caplog.set_level(logging.INFO, logger="api.telemetry")
    repeated = make_event("login_failed")
    api.post(URL, json={"events": [repeated]})
    caplog.clear()

    api.post(URL, json={"events": [make_event("page_viewed"), repeated, 3]})

    assert telemetry_lines(caplog) == [
        "Lote de telemetría: 3 recibidos, 2 guardados (1 repetidos), 1 rechazados | page_viewed, login_failed"
        " | rechazos: events[2] ?: no es un objeto"
    ]


def test_the_log_names_the_failed_field_but_never_copies_values(api, caplog):
    caplog.set_level(logging.INFO, logger="api.telemetry")
    secret = "ana@brasaland.com"
    outside_allowlist = make_event("login_failed", properties={"failure_reason": "invalid_credentials", "email": secret})
    key_with_data = make_event("login_failed", properties={"failure_reason": "invalid_credentials", secret: 1})
    bad_user = make_event(userId=secret)

    api.post(URL, json={"events": [outside_allowlist, key_with_data, bad_user]})

    [line] = telemetry_lines(caplog)
    assert "events[0] login_failed: properties.email: fuera del allowlist" in line
    assert "events[1] login_failed: properties.<clave no válida>: fuera del allowlist" in line
    assert "events[2] page_viewed: userId: uuid_parsing" in line
    assert secret not in line


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
    response = api.post(URL, json={"events": [make_event()]}, headers={"Origin": BACKOFFICE})

    assert response.headers["access-control-allow-origin"] == BACKOFFICE


def test_the_rest_of_the_api_has_no_cors(api):
    response = preflight(api, "/api/v1/auth/login", BACKOFFICE)

    assert "access-control-allow-origin" not in response.headers
    response = api.get("/health", headers={"Origin": BACKOFFICE})
    assert "access-control-allow-origin" not in response.headers
