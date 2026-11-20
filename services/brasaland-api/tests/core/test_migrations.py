"""Las tablas que la API tiene en Supabase quedan cerradas a su API REST (migraciones 002, 003 y 004).

Supabase publica las tablas de `public` a los roles `anon` y `authenticated`. Cada tabla de la API
necesita RLS activado y los permisos de esos roles retirados en alguna migración; si se añade un
modelo nuevo sin hacerlo, esta prueba falla.
"""

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
