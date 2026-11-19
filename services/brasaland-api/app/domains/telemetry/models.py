"""Modelo ORM de la tabla `telemetry_events` (plan de telemetría, sección 14).

Una fila por evento válido. La tabla solo admite inserciones: este dominio nunca la actualiza ni
borra filas, y en Supabase un trigger lo impide (`migrations/002_telemetry_events.sql`).

**Registro propio.** `TelemetryEventRow` no hereda el `metadata` global de SQLModel, así que el
`create_all` de `init_db` (que crea las tablas del inventario al arrancar) no la conoce. En Supabase la
tabla la crea solo la migración 002, con su índice GIN, su trigger y RLS; las pruebas la crean en SQLite
con `TELEMETRY_METADATA.create_all`.

**SQLAlchemy.** Este dominio importa SQLAlchemy directamente (el registro, `Numeric`, `JSON` y `JSONB`,
y el `insert` de cada dialecto en el servicio): es la excepción acotada a la regla del Hito 5, porque
`sqlmodel` no expone `ON CONFLICT` ni `JSONB` (`docs/BRIEFING_DIVERGENCES.md`).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import registry
from sqlmodel import Field, SQLModel

TABLE_NAME = "telemetry_events"

# JSONB en PostgreSQL (índice GIN y operadores como @>); JSON en SQLite, para las pruebas.
TAGS_TYPE = JSON().with_variant(JSONB(), "postgresql")


class TelemetryBase(SQLModel, registry=registry()):
    """Base con un registro (y un `metadata`) propio, fuera del `create_all` de `init_db`."""


TELEMETRY_METADATA = TelemetryBase.metadata


class TelemetryEventRow(TelemetryBase, table=True):
    """Un evento de telemetría guardado. Las columnas y su origen están en el plan, sección 14.2."""

    __tablename__ = TABLE_NAME

    # El eventId del envelope: un reintento del mismo evento no crea otra fila (ON CONFLICT).
    id: uuid.UUID = Field(primary_key=True)
    # Momento del hecho (del envelope), no el de la recepción.
    timestamp: datetime
    # backoffice, api, bff o process (del campo `source` del envelope).
    service: str
    event_type: str
    # info, warn o error: `x-level` del esquema del evento.
    level: str = "info"
    # Métrica principal (`x-value` del esquema); su unidad la da `event_type`.
    value: Decimal | None = Field(default=None, sa_type=Numeric)
    # Resumen legible (`x-message` del esquema), de 200 caracteres como máximo.
    message: str | None = None
    # `properties` del evento más session_id, user_id, request_id, schema_version y environment.
    tags: dict[str, Any] = Field(default_factory=dict, sa_type=TAGS_TYPE)
