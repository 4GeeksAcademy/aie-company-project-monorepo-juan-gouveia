"""Configuración de la instancia de Celery (decisión T10 del plan) y lectura de REDIS_URL."""

import pytest
from brasaland_tasks import celery_app
from brasaland_tasks.celery_app import MissingRedisUrl, create_app, redis_url

URL = "redis://redis:6379/0"


@pytest.fixture
def conf():
    return create_app(URL).conf


def test_redis_is_broker_and_result_backend(conf):
    assert conf.broker_url == URL
    assert conf.result_backend == URL


def test_module_app_uses_redis_url_from_environment():
    assert celery_app.app.conf.broker_url == "redis://localhost:6379/15"
    assert celery_app.app.conf.result_backend == "redis://localhost:6379/15"


def test_ack_only_after_success_and_one_message_at_a_time(conf):
    assert conf.task_acks_late is True
    assert conf.task_reject_on_worker_lost is True
    assert conf.worker_prefetch_multiplier == 1


def test_every_task_has_a_timeout(conf):
    assert conf.task_soft_time_limit == 60
    assert conf.task_time_limit == 90
    assert conf.task_soft_time_limit < conf.task_time_limit


def test_visibility_timeout_exceeds_longest_retry_wait_plus_hard_limit(conf):
    longest_countdown = 40
    assert conf.broker_transport_options["visibility_timeout"] == 300
    assert conf.broker_transport_options["visibility_timeout"] > longest_countdown + conf.task_time_limit
    assert conf.result_backend_transport_options["visibility_timeout"] == 300


def test_only_json_is_accepted(conf):
    assert conf.task_serializer == "json"
    assert conf.result_serializer == "json"
    assert list(conf.accept_content) == ["json"]


def test_started_state_is_tracked_and_results_last_a_day(conf):
    assert conf.task_track_started is True
    assert conf.result_expires == 24 * 60 * 60


def test_queues_are_default_and_dead_letter(conf):
    assert conf.task_default_queue == "default"
    assert [queue.name for queue in conf.task_queues] == ["default", "dead_letter"]


def test_each_queue_has_its_own_exchange_and_routing_key(conf):
    # Si compartieran la clave, cada mensaje de `default` se copiaría también en `dead_letter`.
    for queue in conf.task_queues:
        assert queue.exchange.name == queue.name
        assert queue.routing_key == queue.name


def test_events_for_flower_and_retry_on_startup(conf):
    assert conf.worker_send_task_events is True
    assert conf.task_send_sent_event is True
    assert conf.broker_connection_retry_on_startup is True
    assert conf.worker_concurrency == 2


def test_redis_url_is_required(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(MissingRedisUrl, match="Falta REDIS_URL"):
        redis_url()


def test_blank_redis_url_counts_as_missing(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "   ")
    with pytest.raises(MissingRedisUrl, match="Falta REDIS_URL"):
        redis_url()


def test_redis_url_must_be_a_redis_url(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "amqp://localhost")
    with pytest.raises(MissingRedisUrl, match="redis://"):
        redis_url()


@pytest.mark.parametrize("url", ["redis://localhost:6379/0", "rediss://user:secret@host:6380/1"])
def test_redis_url_accepts_redis_and_tls(monkeypatch, url):
    monkeypatch.setenv("REDIS_URL", f" {url} ")
    assert redis_url() == url
