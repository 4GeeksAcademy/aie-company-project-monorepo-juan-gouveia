"""`TaskQueue` sin HTTP: los casos de la deduplicación y de los estados que el router no alcanza."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domains.tasks.queue import OWNER_KEY, TaskQueue, error_summary, project_state
from tests.tasks.fakes import FakeCelery, FakeRedis

DEDUPE = "brasaland:tasks:dedupe:telemetry.report:now|now"


@pytest.fixture
def parts():
    return FakeCelery(), FakeRedis()


@pytest.fixture
def queue(parts):
    celery, redis = parts
    return TaskQueue(celery, redis, registry_ttl_seconds=86400)


def submit(queue):
    return queue.submit("telemetry.report", {"start": "a", "end": "b"}, owner_id="u1", dedupe_key="now|now")


def test_registries_last_as_long_as_the_results(queue, parts):
    _, redis = parts
    task_id = submit(queue)

    assert redis.ttls[DEDUPE] == 86400
    assert redis.ttls[OWNER_KEY.format(task_id=task_id)] == 86400


def test_a_concurrent_identical_request_reuses_the_winner(parts):
    celery, _ = parts

    class RacingRedis(FakeRedis):
        """La primera lectura no ve nada; mientras, otra petición registra su tarea."""

        def __init__(self):
            super().__init__()
            self.first_get = True

        def get(self, name):
            if name == DEDUPE and self.first_get:
                self.first_get = False
                super().set(DEDUPE, "winner-id")
                return None
            return super().get(name)

    racing = TaskQueue(celery, RacingRedis(), registry_ttl_seconds=86400)

    assert submit(racing) == "winner-id"
    assert celery.sent == []


def test_a_registry_whose_owner_expired_is_replaced(queue, parts):
    celery, redis = parts
    first = submit(queue)
    redis.delete(OWNER_KEY.format(task_id=first))

    second = submit(queue)

    assert second != first
    assert redis.get(DEDUPE) == second.encode()
    assert len(celery.sent) == 2


def test_a_success_without_date_is_not_reused(queue, parts):
    celery, _ = parts
    first = submit(queue)
    celery.finish(first, "SUCCESS", {}, date_done=None)

    assert submit(queue) != first


def test_a_naive_date_done_is_read_as_utc(queue, parts):
    celery, _ = parts
    first = submit(queue)
    naive_recent = (datetime.now(UTC) - timedelta(seconds=10)).replace(tzinfo=None)
    celery.finish(first, "SUCCESS", {}, date_done=naive_recent)

    assert submit(queue) == first


def test_without_dedupe_key_every_submit_is_a_new_task(queue, parts):
    celery, redis = parts
    ids = {queue.submit("telemetry.report", {}, owner_id="u1") for _ in range(2)}

    assert len(ids) == 2
    assert len(celery.sent) == 2
    assert not any(key.startswith("brasaland:tasks:dedupe:") for key in redis.values)


@pytest.mark.parametrize(
    ("state", "status"),
    [
        ("PENDING", "pending"),
        ("RECEIVED", "pending"),
        ("RETRY", "pending"),
        ("STARTED", "started"),
        ("SUCCESS", "success"),
        ("FAILURE", "failure"),
        ("REVOKED", "failure"),
        ("ALGO_NUEVO", "pending"),
    ],
)
def test_celery_states_are_projected_to_the_four_of_the_ticket(state, status):
    assert project_state(state) == status


@pytest.mark.parametrize(
    ("error", "summary"),
    [
        (ValueError("dato\n[SQL: SELECT 1]"), "ValueError: dato"),
        (ValueError(), "ValueError"),
        ("texto\notra línea", "texto"),
        (None, "La tarea falló."),
    ],
)
def test_error_summary_keeps_the_type_and_the_first_line(error, summary):
    assert error_summary(error) == summary


# --- Conexiones al arrancar -------------------------------------------------------------------------------


class _Connection:
    def __init__(self, log):
        self.log = log

    def ensure_connection(self, max_retries=None):
        self.log.append(("broker", max_retries))


class _Producer:
    def __init__(self, log):
        self.connection = _Connection(log)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _ProducerPool:
    def __init__(self, log):
        self.log = log

    def acquire(self, block=False):
        return _Producer(self.log)


class _Backend:
    def __init__(self, log):
        self.client = type("Client", (), {"ping": lambda _self: log.append(("backend", None))})()


class WarmCelery(FakeCelery):
    def __init__(self, log):
        super().__init__()
        self.backend = _Backend(log)
        self.producer_pool = _ProducerPool(log)


def test_warm_up_opens_the_registry_backend_and_broker_connections():
    log = []

    class PingRedis(FakeRedis):
        def ping(self):
            log.append(("registry", None))
            return True

    TaskQueue(WarmCelery(log), PingRedis(), registry_ttl_seconds=60).warm_up()

    assert log == [("registry", None), ("backend", None), ("broker", 1)]


def test_warm_up_with_redis_down_is_unavailable():
    from app.domains.tasks.queue import TaskQueueUnavailable

    class DownRedis(FakeRedis):
        def ping(self):
            from redis.exceptions import ConnectionError as RedisConnectionError

            raise RedisConnectionError("Connection refused")

    with pytest.raises(TaskQueueUnavailable, match="Connection refused"):
        TaskQueue(WarmCelery([]), DownRedis(), registry_ttl_seconds=60).warm_up()
