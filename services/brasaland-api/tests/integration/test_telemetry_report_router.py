"""Pruebas HTTP de `POST /telemetry/report` (ticket #DEV-55, decisiones T2, T6 y T14).

La ruta valida el período, encola `telemetry.report` y responde `202 {"task_id"}`. La cola es la real
(`TaskQueue`) sobre Redis y Celery falsos (fixture `task_queue` del conftest): `task_queue.celery.sent`
son los mensajes encolados y `finish` hace de worker. El contenido del informe se prueba en
`tests/telemetry/test_report_task_contract.py`.
"""

import logging
from datetime import UTC, datetime, timedelta

import pytest

from app.domains.telemetry import router as telemetry_router
from app.domains.users.models import Role

URL = "/telemetry/report"
NOW = datetime(2026, 11, 20, 10, 30, 15, tzinfo=UTC)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    """Fija "ahora" para que el período por defecto sea predecible."""
    monkeypatch.setattr(telemetry_router, "utc_now", lambda: NOW)


@pytest.fixture
def admin(make_user):
    return make_user("admin@brasaland.com", role=Role.ADMIN)


@pytest.fixture
def admin_headers(admin):
    return admin[1]


def sent(task_queue) -> list[dict]:
    return task_queue.celery.sent


# --- Acceso -----------------------------------------------------------------------------------------------


def test_without_token_is_401(api, task_queue):
    assert api.post(URL).status_code == 401
    assert sent(task_queue) == []


def test_a_user_who_is_not_admin_gets_403(api, auth_headers, task_queue):
    assert api.post(URL, headers=auth_headers).status_code == 403
    assert sent(task_queue) == []


def test_authentication_is_checked_before_the_dates(api):
    assert api.post(URL, json={"start_date": "ayer"}).status_code == 401


# --- Encolar ----------------------------------------------------------------------------------------------


def test_answers_202_with_the_task_id_and_enqueues_only_references(api, admin, task_queue):
    user, headers = admin

    response = api.post(URL, headers=headers)

    assert response.status_code == 202
    task_id = response.json()["task_id"]
    assert response.json() == {"task_id": task_id}
    assert response.headers["Location"] == f"/tasks/{task_id}"
    # Sin fechas: los 7 días anteriores a "ahora", resueltos una vez en la API.
    assert sent(task_queue) == [
        {
            "name": "telemetry.report",
            "task_id": task_id,
            "kwargs": {
                "start": "2026-11-13T10:30:15+00:00",
                "end": "2026-11-20T10:30:15+00:00",
                "requested_by": user.id,
            },
        }
    ]


def test_the_owner_is_registered_before_enqueueing(api, admin, task_queue):
    user, headers = admin
    task_id = api.post(URL, headers=headers).json()["task_id"]

    assert task_queue.owner_of(task_id) == user.id
    assert task_queue.redis.ttls[f"brasaland:tasks:owner:{task_id}"] == 24 * 60 * 60


def test_explicit_dates_set_the_period(api, admin_headers, task_queue):
    response = api.post(URL, headers=admin_headers, json={"start_date": "2026-11-01", "end_date": "2026-11-03"})

    assert response.status_code == 202
    assert sent(task_queue)[0]["kwargs"]["start"] == "2026-11-01T00:00:00+00:00"
    assert sent(task_queue)[0]["kwargs"]["end"] == "2026-11-03T00:00:00+00:00"


def test_an_empty_body_is_the_default_period(api, admin_headers, task_queue):
    assert api.post(URL, headers=admin_headers, json={}).status_code == 202
    assert sent(task_queue)[0]["kwargs"]["start"] == "2026-11-13T10:30:15+00:00"


def test_unknown_fields_are_rejected(api, admin_headers, task_queue):
    response = api.post(URL, headers=admin_headers, json={"from": "2026-11-01"})

    assert response.status_code == 422
    assert sent(task_queue) == []


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"start_date": "ayer"}, "invalid_date"),
        ({"end_date": "2026-02-30"}, "invalid_date"),
        ({"start_date": "2026-11-10", "end_date": "2026-11-10"}, "invalid_period"),
        ({"start_date": "2026-11-21"}, "invalid_period"),
        ({"start_date": "2026-01-01", "end_date": "2026-11-01"}, "period_too_long"),
    ],
)
def test_bad_dates_are_422_with_their_code_and_nothing_is_enqueued(api, admin_headers, task_queue, body, code):
    response = api.post(URL, headers=admin_headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert sent(task_queue) == []


# --- Deduplicación (T2 y T14) -----------------------------------------------------------------------------


def test_the_same_request_while_the_task_is_alive_returns_the_same_task_id(api, admin_headers, task_queue):
    first = api.post(URL, headers=admin_headers).json()["task_id"]
    task_queue.celery.finish(first, "STARTED")
    second = api.post(URL, headers=admin_headers).json()["task_id"]

    assert second == first
    assert len(sent(task_queue)) == 1


def test_a_task_waiting_for_a_retry_is_still_reused(api, admin_headers, task_queue):
    first = api.post(URL, headers=admin_headers).json()["task_id"]
    task_queue.celery.finish(first, "RETRY")

    assert api.post(URL, headers=admin_headers).json()["task_id"] == first


def test_equivalent_spellings_of_a_date_share_the_task(api, admin_headers, task_queue):
    ids = {
        api.post(URL, headers=admin_headers, json={"start_date": spelling}).json()["task_id"]
        for spelling in ("2026-11-14", "2026-11-14T00:00:00Z", "2026-11-14T02:00:00+02:00")
    }

    assert len(ids) == 1
    assert len(sent(task_queue)) == 1


def test_each_combination_of_dates_has_its_own_task(api, admin_headers, task_queue):
    default = api.post(URL, headers=admin_headers).json()["task_id"]
    explicit = api.post(URL, headers=admin_headers, json={"start_date": "2026-11-14"}).json()["task_id"]

    assert default != explicit
    assert len(sent(task_queue)) == 2


def test_a_success_is_reused_for_60_seconds_as_a_cache(api, admin_headers, task_queue):
    first = api.post(URL, headers=admin_headers).json()["task_id"]
    task_queue.celery.finish(first, "SUCCESS", {"period": {}}, date_done=datetime.now(UTC) - timedelta(seconds=30))

    assert api.post(URL, headers=admin_headers).json()["task_id"] == first
    assert len(sent(task_queue)) == 1


def test_after_60_seconds_a_success_is_recalculated(api, admin_headers, task_queue):
    first = api.post(URL, headers=admin_headers).json()["task_id"]
    task_queue.celery.finish(first, "SUCCESS", {"period": {}}, date_done=datetime.now(UTC) - timedelta(seconds=61))

    second = api.post(URL, headers=admin_headers).json()["task_id"]

    assert second != first
    assert len(sent(task_queue)) == 2
    # El registro apunta ya a la tarea nueva.
    assert api.post(URL, headers=admin_headers).json()["task_id"] == second


def test_after_a_failure_the_request_enqueues_a_new_task(api, admin_headers, task_queue):
    first = api.post(URL, headers=admin_headers).json()["task_id"]
    task_queue.celery.finish(first, "FAILURE", RuntimeError("boom"))

    second = api.post(URL, headers=admin_headers).json()["task_id"]

    assert second != first
    assert len(sent(task_queue)) == 2


# --- Cola no disponible -----------------------------------------------------------------------------------


def test_redis_down_is_503_and_is_logged(api, admin_headers, task_queue, caplog):
    task_queue.redis.down = True
    caplog.set_level(logging.ERROR, logger="api.telemetry")

    response = api.post(URL, headers=admin_headers)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "task_queue_unavailable"
    assert any("Connection refused" in r.getMessage() for r in caplog.records if r.name == "api.telemetry")


def test_a_failed_publish_leaves_no_registry_behind(api, admin_headers, task_queue):
    task_queue.celery.broker_down = True

    failed = api.post(URL, headers=admin_headers)

    assert failed.status_code == 503
    assert task_queue.redis.values == {}
    task_queue.celery.broker_down = False
    recovered = api.post(URL, headers=admin_headers)
    assert recovered.status_code == 202
    assert len(sent(task_queue)) == 1


def test_without_redis_url_the_route_is_503(api, admin_headers, monkeypatch):
    from app.domains.tasks import dependencies
    from app.main import app

    app.dependency_overrides.pop(dependencies.get_task_queue, None)
    dependencies._default_queue.cache_clear()
    monkeypatch.delenv("REDIS_URL", raising=False)

    response = api.post(URL, headers=admin_headers)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "task_queue_unavailable"


# --- Contrato ---------------------------------------------------------------------------------------------


def test_openapi_documents_the_body_and_the_202_and_there_is_no_get(api):
    operations = api.get("/openapi.json").json()["paths"][URL]

    assert set(operations) == {"post"}
    operation = operations["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"]["anyOf"][0] == {
        "$ref": "#/components/schemas/TelemetryReportRequest"
    }
    assert operation["responses"]["202"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/TaskAccepted"
    }
