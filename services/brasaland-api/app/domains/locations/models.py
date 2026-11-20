"""Modelo ORM de la tabla `locations`: los 14 locales de Brasaland.

El `id` es el `location_id` (1–14) que ya usan las órdenes del inventario y la telemetría; la tabla le
da su sede (`code` y `name` del briefing del gestor de incidencias), su ciudad, su país y su moneda.

**Registro propio**, como `telemetry_events`: el `create_all` de `init_db` no conoce este modelo. En
Supabase la tabla la crea y la llena solo `migrations/004_locations.sql`, con RLS; así nunca existe
vacía ni abierta a la API REST de Supabase. Las pruebas la crean en SQLite con `LOCATIONS_METADATA`.

La API solo la lee.
"""

from sqlalchemy.orm import registry
from sqlmodel import Field, SQLModel

TABLE_NAME = "locations"


class LocationsBase(SQLModel, registry=registry()):
    """Base con un registro (y un `metadata`) propio, fuera del `create_all` de `init_db`."""


LOCATIONS_METADATA = LocationsBase.metadata


class Location(LocationsBase, table=True):
    """Un local de Brasaland. Las filas y sus restricciones están en la migración 004."""

    __tablename__ = TABLE_NAME

    # El location_id de las órdenes y de los eventos de telemetría (1–14).
    id: int = Field(primary_key=True)
    # Código de la sede del briefing del gestor de incidencias (`branch`), p. ej. `medellin_centro`.
    code: str = Field(unique=True)
    # Nombre para mostrar del briefing, p. ej. "Medellín Centro".
    name: str
    city: str
    # CO o US.
    country: str
    # COP en Colombia, USD en Florida.
    currency: str
