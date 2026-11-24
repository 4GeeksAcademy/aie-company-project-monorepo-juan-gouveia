"""Base SQLite con `ops.job_runs` como en la migración 006 (el esquema `ops`, adjuntado como otra base).

Las restricciones y los dos índices de la tabla (`job_runner.metadata`) valen igual en
SQLite, incluido el índice único parcial de `processing`, así que el lock se prueba de verdad.
"""

from datetime import UTC, datetime, timedelta

import pytest
from brasaland_jobs import job_runner
from sqlalchemy import create_engine, event


@pytest.fixture
def engine(tmp_path):
    main_db = tmp_path / "main.db"
    ops_db = tmp_path / "ops.db"
    engine = create_engine(f"sqlite:///{main_db.as_posix()}")

    @event.listens_for(engine, "connect")
    def attach_ops(dbapi_connection, _record):
        dbapi_connection.execute(f"ATTACH DATABASE '{ops_db.as_posix()}' AS ops")

    job_runner.metadata.create_all(engine)
    yield engine
    engine.dispose()


class Clock:
    """Reloj controlable: cada lectura avanza 1 s, para que los timestamps sean distintos y ordenados."""

    def __init__(self, start: datetime = datetime(2026, 11, 25, 8, 0, tzinfo=UTC)) -> None:
        self.now = start

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock():
    return Clock()
