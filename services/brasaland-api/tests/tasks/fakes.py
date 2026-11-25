"""Redis y Celery falsos para probar la cola de tareas sin servidor (ticket #DEV-55).

`FakeRedis` imita lo que usa `TaskQueue` de redis-py (`get` devuelve bytes, `set` con `ex` y `nx`).
`FakeCelery` imita `send_task` y `AsyncResult`: cada tarea encolada empieza en `PENDING`, y la prueba la
lleva a otro estado con `finish`, como haría el worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from kombu.exceptions import OperationalError as KombuOperationalError
from redis.exceptions import ConnectionError as RedisConnectionError


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.ttls: dict[str, int | None] = {}
        self.down = False

    def _check(self) -> None:
        if self.down:
            raise RedisConnectionError("Error 10061 connecting to 127.0.0.1:6379. Connection refused.")

    def get(self, name: str) -> bytes | None:
        self._check()
        return self.values.get(name)

    def set(self, name: str, value: str, ex: int | None = None, nx: bool = False) -> bool | None:
        self._check()
        if nx and name in self.values:
            return None
        self.values[name] = str(value).encode()
        self.ttls[name] = ex
        return True

    def delete(self, *names: str) -> int:
        self._check()
        removed = sum(1 for name in names if self.values.pop(name, None) is not None)
        for name in names:
            self.ttls.pop(name, None)
        return removed


@dataclass
class FakeResult:
    state: str = "PENDING"
    result: Any = None
    date_done: datetime | None = None


@dataclass
class FakeCelery:
    sent: list[dict[str, Any]] = field(default_factory=list)
    results: dict[str, FakeResult] = field(default_factory=dict)
    broker_down: bool = False

    def send_task(self, name: str, kwargs: dict[str, Any] | None = None, task_id: str | None = None) -> None:
        if self.broker_down:
            raise KombuOperationalError("[WinError 10061] No connection could be made")
        self.sent.append({"name": name, "kwargs": kwargs, "task_id": task_id})

    def AsyncResult(self, task_id: str) -> FakeResult:  # mismo nombre que en Celery
        return self.results.get(task_id, FakeResult())

    def finish(self, task_id: str, state: str, result: Any = None, date_done: datetime | None = None) -> None:
        self.results[task_id] = FakeResult(state=state, result=result, date_done=date_done)
