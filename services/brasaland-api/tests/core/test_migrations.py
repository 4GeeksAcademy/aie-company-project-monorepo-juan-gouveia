"""Las tablas de Supabase quedan cerradas a su API REST (migraciones 002 a 006).

Supabase publica las tablas de `public` a los roles `anon` y `authenticated`. Cada tabla de la API
necesita RLS activado y los permisos de esos roles retirados en alguna migración; si se añade un
modelo nuevo sin hacerlo, esta prueba falla.
"""

import re
from pathlib import Path

from sqlmodel import SQLModel

import app.domains.inventory.models  # noqa: F401  (registra las tablas del inventario)
from app.domains.locations.models import LOCATIONS_METADATA
from app.domains.telemetry.models import TELEMETRY_METADATA

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def all_migrations() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(MIGRATIONS.glob("*.sql")))


def api_tables() -> set[str]:
    return set(SQLModel.metadata.tables) | set(TELEMETRY_METADATA.tables) | set(LOCATIONS_METADATA.tables)


def test_every_api_table_has_row_level_security():
    sql = all_migrations()
    assert api_tables() == {"ingredients", "ingredient_entries", "ingredient_exits", "telemetry_events", "locations"}
    for table in api_tables():
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql, table


def test_every_api_table_is_revoked_from_the_supabase_rest_roles():
    revokes = [line for line in all_migrations().splitlines() if line.startswith("REVOKE ALL ON ")]
    for table in api_tables():
        assert any(table in line and line.endswith("FROM anon, authenticated;") for line in revokes), table


# Tablas que crean las migraciones, con su esquema si no es `public` (p. ej. `ops.job_runs`). Las de
# `reporting` y `ops` no son modelos de la API (las usan el pipeline y el script nocturno), así que las
# dos pruebas anteriores no las ven.
CREATE_TABLE = re.compile(r"^create table if not exists ([a-z_][a-z0-9_.]*)", re.IGNORECASE | re.MULTILINE)


def migration_tables() -> set[str]:
    return set(CREATE_TABLE.findall(all_migrations()))


def test_every_migration_table_is_closed_to_the_supabase_rest_roles():
    sql = all_migrations()
    revokes = [line for line in sql.splitlines() if line.startswith("REVOKE ALL ON ")]
    tables = migration_tables()
    assert {"telemetry_events", "locations", "reporting.pipeline_runs", "ops.job_runs"} <= tables
    for table in tables:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql, table
        assert f"REVOKE ALL ON {table} FROM anon, authenticated;" in revokes, table
        if "." in table:
            schema = table.split(".", 1)[0]
            assert f"REVOKE ALL ON SCHEMA {schema} FROM anon, authenticated;" in revokes, table


def job_runs_sql() -> str:
    return (MIGRATIONS / "006_job_runs.sql").read_text(encoding="utf-8")


def test_job_runs_status_values_are_the_ticket_ones():
    # Los cuatro estados del ticket #DEV-53, exactos y en el orden de la máquina de estados.
    assert "CHECK (status IN ('pending', 'processing', 'completed', 'failed'))" in job_runs_sql()


def test_job_runs_lock_is_the_processing_status():
    # El lock es el estado (decisión N9): un índice único parcial sobre processing, sin tabla ni columna
    # de lock aparte; y el índice de idempotencia por (job_name, target_date) que pide el ticket.
    sql = " ".join(job_runs_sql().split())
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_job_runs_one_processing ON ops.job_runs (job_name) WHERE status = 'processing';" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_job_runs_job_name_target_date ON ops.job_runs (job_name, target_date);" in sql
