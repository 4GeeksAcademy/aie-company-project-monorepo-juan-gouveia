"""Entorno de las pruebas del pipeline: Prefect temporal y una base SQLite con las mismas tablas.

- Prefect corre contra un servidor temporal (`prefect_test_harness`) y guarda los resultados cacheados
  en una carpeta temporal, nunca en ~/.prefect.
- La base es SQLite: `telemetry_events` y `locations` como en las migraciones 002 y 004, y el esquema
  `reporting` (adjuntado como otra base) con las tablas de `repository.metadata`, como en la 005.
- Los eventos son sintéticos y solo existen aquí: nunca se escriben en Supabase.
"""

import os
import tempfile

# Antes de importar Prefect: los resultados cacheados de las pruebas no se mezclan con los reales.
os.environ["PREFECT_RESULTS_LOCAL_STORAGE_PATH"] = tempfile.mkdtemp(prefix="prefect-results-")

from datetime import UTC, datetime
from itertools import count

import pytest
from brasaland_pipelines import pipeline, repository
from prefect.testing.utilities import prefect_test_harness
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    event,
    insert,
)

CODES = [
    "medellin_centro", "medellin_laureles", "medellin_envigado", "medellin_bello", "medellin_itagui",
    "bogota_chapinero", "bogota_usaquen", "cali_granada", "barranquilla_norte",
    "miami_doral", "miami_hialeah", "miami_kendall", "orlando_international", "fort_lauderdale",
]

source = MetaData()
telemetry_events = Table(
    "telemetry_events",
    source,
    Column("id", Text, primary_key=True),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("service", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("level", Text),
    Column("value", Text),
    Column("message", Text),
    Column("tags", JSON),
)
locations = Table(
    "locations",
    source,
    Column("id", Integer, primary_key=True),
    Column("code", Text),
    Column("name", Text),
    Column("city", Text),
    Column("country", Text),
    Column("currency", Text),
)


@pytest.fixture(scope="session", autouse=True)
def prefect_server():
    with prefect_test_harness():
        yield


@pytest.fixture
def database(tmp_path, monkeypatch):
    """Base SQLite nueva por prueba, con el pipeline apuntando a ella y a carpetas temporales."""
    main_db = tmp_path / "main.db"
    reporting_db = tmp_path / "reporting.db"
    url = f"sqlite:///{main_db.as_posix()}"
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def attach_reporting(dbapi_connection, _record):
        dbapi_connection.execute(f"ATTACH DATABASE '{reporting_db.as_posix()}' AS reporting")

    source.create_all(engine)
    repository.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            insert(locations),
            [
                {
                    "id": i,
                    "code": code,
                    "name": code.replace("_", " ").title(),
                    "city": code.split("_")[0],
                    "country": "CO" if i <= 9 else "US",
                    "currency": "COP" if i <= 9 else "USD",
                }
                for i, code in enumerate(CODES, start=1)
            ],
        )

    monkeypatch.setenv("REPORTING_DATABASE_URL", url)
    monkeypatch.setattr(pipeline, "get_engine", lambda: engine)
    monkeypatch.setattr(pipeline, "RAW_DIR", tmp_path / "raw" / "telemetry_events")
    monkeypatch.setattr(pipeline, "EVAL_DIR", tmp_path / "eval" / "weekly_location_performance")
    yield engine
    engine.dispose()


_ids = count(1)


def add_event(engine, event_type, *, timestamp, location_id=3, environment="production", **props):
    """Inserta un evento sintético con el envelope en `tags`, como lo guarda el receptor."""
    country, currency = ("CO", "COP") if location_id <= 9 else ("US", "USD")
    tags = {
        "location_id": location_id,
        "country": country,
        "currency": currency,
        **props,
        "session_id": "0f8e7d6c-5b4a-4392-8170-6e5d4c3b2a19",
        "user_id": "d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2",
        "request_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        "schema_version": "1.0.0",
        "environment": environment,
    }
    event_id = f"00000000-0000-4000-8000-{next(_ids):012d}"
    with engine.begin() as conn:
        conn.execute(
            insert(telemetry_events).values(
                id=event_id,
                timestamp=datetime.fromisoformat(timestamp).astimezone(UTC),
                service="backoffice",
                event_type=event_type,
                tags=tags,
            )
        )
    return event_id
