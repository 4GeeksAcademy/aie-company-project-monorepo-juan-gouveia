"""El catálogo de locales de las pruebas sale de la propia migración 004: no hay una segunda lista."""

import re
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session

from app.domains.locations.models import LOCATIONS_METADATA, Location

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "004_locations.sql"

ROW = re.compile(r"\((\d+), '([a-z_]+)', '([^']+)', '([^']+)', '(CO|US)', '(COP|USD)'\)")


def migration_rows() -> list[dict]:
    """Las filas del `INSERT` de la migración 004, en su orden."""
    sql = MIGRATION.read_text(encoding="utf-8")
    return [
        {"id": int(id_), "code": code, "name": name, "city": city, "country": country, "currency": currency}
        for id_, code, name, city, country, currency in ROW.findall(sql)
    ]


def seed_locations(engine: Engine) -> None:
    """Crea la tabla `locations` y la llena como la migración 004."""
    LOCATIONS_METADATA.create_all(engine)
    with Session(engine) as session:
        session.add_all(Location(**row) for row in migration_rows())
        session.commit()
