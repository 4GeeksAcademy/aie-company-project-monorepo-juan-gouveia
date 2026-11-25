"""Pruebas HTTP de `GET /tasks/{task_id}` (ticket #DEV-55, decisiones T4 y T5).

Cada tarea se encola por la API real (`POST /telemetry/report`) y el worker se simula con
`task_queue.celery.finish`, que deja en el backend falso el estado que dejaría Celery.
"""

import logging
from uuid import uuid4

import pytest

from app.domains.users.models import Role

pytestmark = pytest.mark.integration

REPORT = {"period": {"from": "2026-11-13T10:30:15Z", "to": "2026-11-20T10:30:15Z"}, "metrics": {}}


@pytest.fixture
def admin_headers(make_user):
    return make_user("admin@brasaland.com", role=Role.ADMIN)[1]


@pytest.fixture
def task_id(api, admin_headers):
    return api.post("/telemetry/report", headers=admin_headers).json()["task_id"]


def get_task(api, task_id, headers):
    return api.get(f"/tasks/{task_id}", headers=headers)


# --- Ciclo de vida ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("celery_state", "status"),
    [("PENDING", "pending"), ("RECEIVED", "pending"), ("RETRY", "pending"), ("STARTED", "started")],
)
def test_states_before_the_end_have_no_result(api, admin_headers, task_queue, task_id, celery_state, status):
    task_queue.celery.finish(task_id, celery_state)

    response = get_task(api, task_id, admin_headers)

    assert response.status_code == 200
    assert response.json() == {"task_id": task_id, "status": status, "result": None}


def test_a_freshly_enqueued_task_is_pending(api, admin_headers, task_id):
    assert get_task(api, task_id, admin_headers).json()["status"] == "pending"


def test_success_returns_the_report(api, admin_headers, task_queue, task_id):
    task_queue.celery.finish(task_id, "SUCCESS", REPORT)

    assert get_task(api, task_id, admin_headers).json() == {"task_id": task_id, "status": "success", "result": REPORT}


def test_failure_returns_only_the_first_line_of_the_error(api, admin_headers, task_queue, task_id):
    error = RuntimeError("(psycopg2.OperationalError) connection refused\n[SQL: SELECT ... FROM telemetry_events]")
    task_queue.celery.finish(task_id, "FAILURE", error)

    body = get_task(api, task_id, admin_headers).json()

    assert body["status"] == "failure"
    assert body["result"] == {"error": "RuntimeError: (psycopg2.OperationalError) connection refused"}


def test_a_revoked_task_counts_as_failure(api, admin_headers, task_queue, task_id):
    task_queue.celery.finish(task_id, "REVOKED", None)

    body = get_task(api, task_id, admin_headers).json()

    assert body["status"] == "failure"
    assert body["result"] == {"error": "La tarea falló."}


def test_the_status_values_are_exactly_the_four_of_the_ticket(api):
    schema = api.get("/openapi.json").json()["components"]["schemas"]["TaskStatus"]

    assert schema["properties"]["status"]["enum"] == ["pending", "started", "success", "failure"]
    assert set(schema["properties"]) == {"task_id", "status", "result"}


# --- Acceso (T4) ------------------------------------------------------------------------------------------


def test_without_token_is_401(api, task_id):
    assert api.get(f"/tasks/{task_id}").status_code == 401


def test_an_unknown_id_is_404(api, admin_headers):
    response = get_task(api, str(uuid4()), admin_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "task_not_found"


def test_an_id_that_is_not_a_uuid_is_404_without_touching_redis(api, admin_headers, task_queue):
    task_queue.redis.down = True

    assert get_task(api, "no-es-un-id", admin_headers).status_code == 404


def test_another_user_gets_404_as_if_it_did_not_exist(api, task_id, make_user):
    _, other = make_user("otra@brasaland.com")

    response = get_task(api, task_id, other)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "task_not_found"


def test_another_admin_can_read_it(api, task_id, make_user):
    _, other_admin = make_user("otro-admin@brasaland.com", role=Role.ADMIN)

    assert get_task(api, task_id, other_admin).status_code == 200


def test_the_owner_can_read_it_even_without_being_admin(api, task_queue, make_user):
    # Hoy solo los admin encolan, pero el acceso es por dueño: sirve ya para tareas de otros roles.
    user, headers = make_user("equipo@brasaland.com")
    task_id = task_queue.submit("telemetry.report", {}, owner_id=user.id)

    assert get_task(api, task_id, headers).json()["status"] == "pending"


# --- Cola no disponible -----------------------------------------------------------------------------------


def test_redis_down_is_503_and_is_logged(api, admin_headers, task_queue, task_id, caplog):
    task_queue.redis.down = True
    caplog.set_level(logging.ERROR, logger="api.tasks")

    response = get_task(api, task_id, admin_headers)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "task_queue_unavailable"
    assert any(task_id in r.getMessage() for r in caplog.records if r.name == "api.tasks")


# --- Arranque ---------------------------------------------------------------------------------------------


def test_startup_without_redis_url_warns_and_the_api_still_starts(monkeypatch, caplog):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.delenv("REDIS_URL", raising=False)
    caplog.set_level(logging.WARNING, logger="uvicorn.error")

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    assert any("falta REDIS_URL" in r.getMessage() for r in caplog.records)


def test_startup_with_redis_down_warns_and_the_api_still_starts(monkeypatch, caplog):
    from fastapi.testclient import TestClient

    from app.domains.tasks import dependencies
    from app.domains.tasks.queue import TaskQueueUnavailable
    from app.main import app

    class DownQueue:
        def warm_up(self):
            raise TaskQueueUnavailable("ConnectionError: Connection refused")

    app.dependency_overrides.pop(dependencies.get_task_queue, None)
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")
    monkeypatch.setattr("app.main.get_task_queue", lambda: DownQueue())
    caplog.set_level(logging.WARNING, logger="uvicorn.error")

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    assert any("sin conexión al arrancar" in r.getMessage() for r in caplog.records)
