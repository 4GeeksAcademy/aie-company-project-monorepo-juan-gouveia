"""Conexión del worker: TASKS_DATABASE_URL obligatoria y driver psycopg2 explícito."""

import pytest
from brasaland_tasks import db


@pytest.fixture(autouse=True)
def fresh_engine():
    db.get_engine.cache_clear()
    yield
    db.get_engine.cache_clear()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgresql://task_worker.ref:pw@host:5432/postgres", "postgresql+psycopg2://task_worker.ref:pw@host:5432/postgres"),
        ("postgres://task_worker.ref:pw@host:5432/postgres", "postgresql+psycopg2://task_worker.ref:pw@host:5432/postgres"),
        ("postgresql+psycopg2://u:pw@host/db", "postgresql+psycopg2://u:pw@host/db"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_supabase_urls_use_psycopg2(url, expected):
    # SQLAlchemy 2.1 usaría psycopg (v3), que no está instalado: la primera tarea fallaría.
    assert db.with_psycopg2_driver(url) == expected


@pytest.mark.parametrize("value", [None, "", "   "])
def test_database_url_is_required(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("TASKS_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("TASKS_DATABASE_URL", value)
    with pytest.raises(db.MissingDatabaseUrl, match="task_worker"):
        db.get_engine()


def test_engine_uses_psycopg2_and_is_created_once(monkeypatch):
    monkeypatch.setenv("TASKS_DATABASE_URL", "postgresql://task_worker.ref:pw@127.0.0.1:5432/postgres")
    engine = db.get_engine()
    assert engine.dialect.driver == "psycopg2"
    assert db.get_engine() is engine
