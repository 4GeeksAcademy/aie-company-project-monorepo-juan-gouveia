"""Tabla `telemetry_events`: el modelo, su registro propio y la migración 002 dicen lo mismo."""

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.database import init_db
from app.domains.telemetry.models import TABLE_NAME, TELEMETRY_METADATA, TelemetryEventRow

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "002_telemetry_events.sql"
COLUMNS = ["id", "timestamp", "service", "event_type", "level", "value", "message", "tags"]
INDEXES = ["idx_telemetry_events_timestamp", "idx_telemetry_events_event_type", "idx_telemetry_events_tags"]


def test_the_model_has_the_eight_columns_of_the_contract():
    table = TelemetryEventRow.__table__
    assert [column.name for column in table.columns] == COLUMNS
    assert [column.name for column in table.primary_key] == ["id"]
    nullable = {column.name for column in table.columns if column.nullable}
    assert nullable == {"value", "message"}


def test_the_table_stays_out_of_the_global_metadata_used_at_startup(tmp_path):
    # init_db crea las tablas del inventario al arrancar; la de telemetría solo la crea la migración.
    assert TABLE_NAME not in SQLModel.metadata.tables
    engine = create_engine(f"sqlite:///{tmp_path / 'startup.db'}")
    init_db(engine)
    assert TABLE_NAME not in inspect(engine).get_table_names()


def test_a_row_round_trips_with_its_json_tags(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'telemetry.db'}")
    TELEMETRY_METADATA.create_all(engine)
    event_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            TelemetryEventRow(
                id=event_id,
                timestamp=datetime(2026, 11, 19, 10, 15, 30, 123000, tzinfo=UTC),
                service="backoffice",
                event_type="stock_waste_registered",
                value=Decimal("2.5"),
                tags={"country": "CO", "reason": "expired", "session_id": None},
            )
        )
        session.commit()
        row = session.exec(select(TelemetryEventRow)).one()
    assert row.id == event_id
    assert row.level == "info"
    assert row.value == Decimal("2.5")
    assert row.tags == {"country": "CO", "reason": "expired", "session_id": None}


def test_the_migration_creates_the_same_columns_indexes_and_protections():
    sql = MIGRATION.read_text(encoding="utf-8")
    body = sql.split("CREATE TABLE IF NOT EXISTS telemetry_events (", 1)[1].split(");", 1)[0]
    declared = [line.split()[0] for line in body.strip().splitlines()]
    assert declared == COLUMNS
    for index in INDEXES:
        assert f"CREATE INDEX IF NOT EXISTS {index} ON telemetry_events" in sql
    assert "USING GIN (tags)" in sql
    assert re.search(r"BEFORE UPDATE OR DELETE ON telemetry_events\s+FOR EACH ROW", sql)
    assert re.search(r"BEFORE TRUNCATE ON telemetry_events\s+FOR EACH STATEMENT", sql)
    assert "ALTER TABLE telemetry_events ENABLE ROW LEVEL SECURITY;" in sql


def test_the_telemetry_domain_never_updates_or_deletes():
    domain = Path(__file__).resolve().parents[2] / "app" / "domains" / "telemetry"
    for path in domain.glob("*.py"):
        code = path.read_text(encoding="utf-8")
        for forbidden in (r"\bupdate\(", r"\bdelete\(", r"session\.delete", r"\.merge\(", r"UPDATE ", r"DELETE "):
            assert not re.search(forbidden, code), f"{path.name}: {forbidden}"
