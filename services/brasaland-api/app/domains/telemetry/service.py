"""Almacenamiento de telemetría: validar cada evento, convertirlo en fila y guardar el lote.

Plan de telemetría, sección 14:

1. **Validación por evento.** Cada elemento crudo del lote pasa por `TelemetryEvent.model_validate`
   (el envelope) y después por el catálogo generado desde `event-schemas.json` (tipo conocido,
   propiedades obligatorias y allowlist). Un evento que falla se rechaza solo; el resto sigue.
2. **De evento a fila.** `service` sale de `source`; `level`, `value` y `message`, del catálogo; `tags`
   es `properties` más cinco campos del envelope.
3. **Un solo INSERT por lote.** `INSERT … VALUES (…), (…) ON CONFLICT (id) DO NOTHING`, en una
   transacción: un evento repetido (reintento o `sendBeacon` duplicado) no crea otra fila.

Este dominio importa SQLAlchemy directamente: `sqlmodel` no expone el `insert` de cada dialecto, que es
el que tiene `ON CONFLICT` (excepción acotada a la regla del Hito 5; `docs/BRIEFING_DIVERGENCES.md`).
"""

import json
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.domains.telemetry.catalog import TELEMETRY_CATALOG
from app.domains.telemetry.models import TelemetryEventRow
from app.domains.telemetry.schemas import TelemetryEvent

# `source` del envelope → columna `service` (S1). El navegador es el backoffice.
SERVICE_BY_SOURCE = {"browser": "backoffice", "api": "api", "bff": "bff", "process": "process"}

MESSAGE_MAX_LENGTH = 200
MISSING = "—"
PLACEHOLDER = re.compile(r"\{(\w+)\}")

# Solo estos nombres de clave o tipo se copian en el log de rechazos; cualquier otro se oculta, porque
# un lote malicioso podría poner datos personales en el nombre de una clave.
SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")

INSERTS_BY_DIALECT = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}


class TelemetryStorageError(Exception):
    """La base de datos no pudo guardar el lote; `missing_table` si falta la migración 002."""

    def __init__(self, reason: str, missing_table: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.missing_table = missing_table


@dataclass(frozen=True)
class Rejection:
    """Un evento rechazado, descrito sin copiar ningún valor del evento."""

    index: int
    event_type: str
    reason: str

    def describe(self) -> str:
        return f"events[{self.index}] {self.event_type}: {self.reason}"


@dataclass
class ParsedBatch:
    valid: list[TelemetryEvent] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)


# --- Validación ---------------------------------------------------------------------------------------


def _safe_name(name: Any) -> str:
    return name if isinstance(name, str) and SAFE_NAME.match(name) else "<clave no válida>"


def _event_type_of(raw: Any) -> str:
    event_type = raw.get("event_type") if isinstance(raw, dict) else None
    return event_type if isinstance(event_type, str) and SAFE_NAME.match(event_type) else "?"


def _first_error(error: ValidationError) -> str:
    """El primer campo que falló y por qué, sin el valor recibido."""
    first = error.errors(include_input=False, include_url=False)[0]
    location = ".".join(_safe_name(part) if isinstance(part, str) else f"[{part}]" for part in first["loc"])
    return f"{location or 'evento'}: {first['type']}"


def _has_unstorable_value(value: Any) -> bool:
    """PostgreSQL no admite NaN ni infinitos en JSONB, ni el carácter NUL en un texto."""
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(_has_unstorable_value(key) or _has_unstorable_value(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_unstorable_value(item) for item in value)
    return False


def check_properties(event: TelemetryEvent) -> str | None:
    """Comprueba `properties` contra el catálogo; devuelve el motivo del rechazo o `None` si es válido."""
    entry = TELEMETRY_CATALOG.get(event.event_type)
    if entry is None:
        return "event_type fuera del catálogo"
    for key in event.properties:
        if key not in entry.allowed:
            return f"properties.{_safe_name(key)}: fuera del allowlist"
    for key in entry.required:
        if key not in event.properties:
            return f"properties.{key}: obligatoria"
    if _has_unstorable_value(event.properties):
        return "properties: valor que no se puede guardar (NaN, infinito o carácter NUL)"
    return None


def parse_batch(raw_events: list[Any]) -> ParsedBatch:
    """Valida cada elemento del lote por separado. Nunca lanza: un elemento malo solo se rechaza."""
    parsed = ParsedBatch()
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            parsed.rejections.append(Rejection(index, "?", "no es un objeto"))
            continue
        try:
            event = TelemetryEvent.model_validate(raw)
        except ValidationError as error:
            parsed.rejections.append(Rejection(index, _event_type_of(raw), _first_error(error)))
            continue
        reason = check_properties(event)
        if reason:
            parsed.rejections.append(Rejection(index, event.event_type, reason))
            continue
        parsed.valid.append(event)
    return parsed


# --- De evento a fila ---------------------------------------------------------------------------------


def _text(value: Any) -> str:
    if value is None or value == "" or value == []:
        return MISSING
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, list):
        return ", ".join(_text(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def build_message(template: str, properties: dict[str, Any]) -> str:
    message = PLACEHOLDER.sub(lambda match: _text(properties.get(match.group(1))), template)
    if len(message) > MESSAGE_MAX_LENGTH:
        message = message[: MESSAGE_MAX_LENGTH - 1] + "…"
    return message


def build_value(key: str | None, properties: dict[str, Any]) -> Decimal | None:
    number = properties.get(key) if key else None
    # bool es un int en Python, pero no es una métrica.
    if isinstance(number, bool) or not isinstance(number, int | float):
        return None
    return Decimal(str(number))


def to_row(event: TelemetryEvent) -> dict[str, Any]:
    """La fila de `telemetry_events` de un evento válido (plan de telemetría, sección 14.2)."""
    entry = TELEMETRY_CATALOG[event.event_type]
    envelope = event.model_dump(mode="json", include={"sessionId", "userId", "requestId", "schemaVersion", "environment"})
    tags = {
        **event.properties,
        "session_id": envelope["sessionId"],
        "user_id": envelope["userId"],
        "request_id": envelope["requestId"],
        "schema_version": envelope["schemaVersion"],
        "environment": envelope["environment"],
    }
    return {
        "id": event.eventId,
        "timestamp": event.timestamp,
        "service": SERVICE_BY_SOURCE[event.source],
        "event_type": event.event_type,
        "level": entry.level,
        "value": build_value(entry.value, event.properties),
        "message": build_message(entry.message, event.properties),
        "tags": tags,
    }


# --- Guardado -----------------------------------------------------------------------------------------


def _is_missing_table(error: SQLAlchemyError) -> bool:
    text = str(getattr(error, "orig", error)).lower()
    return "telemetry_events" in text and ("does not exist" in text or "no such table" in text)


def store_events(session: Session, events: list[TelemetryEvent]) -> int:
    """Inserta los eventos con una sola sentencia; devuelve cuántas filas nuevas se escribieron.

    Los repetidos (mismo `eventId`, en este lote o en uno anterior) no escriben nada. Si la base falla,
    deshace la transacción y lanza `TelemetryStorageError`, sin copiar los datos del lote.
    """
    if not events:
        return 0
    rows = [to_row(event) for event in events]
    try:
        insert = INSERTS_BY_DIALECT[session.get_bind().dialect.name]
        statement = insert(TelemetryEventRow).values(rows).on_conflict_do_nothing(index_elements=["id"])
        result = session.exec(statement)
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        # Solo la primera línea del error del driver: las siguientes pueden llevar valores del lote.
        detail = str(getattr(error, "orig", error)).strip()
        reason = detail.splitlines()[0] if detail else "sin detalle"
        raise TelemetryStorageError(f"{type(error).__name__}: {reason}", _is_missing_table(error)) from error
    return result.rowcount
