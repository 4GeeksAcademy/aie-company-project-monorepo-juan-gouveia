"""El informe técnico de telemetría que calcula la tarea `telemetry.report`.

Misma forma que el antiguo `GET /telemetry/report` de la API (`TelemetryReport`): `period` con `from` y
`to` en ISO 8601 UTC y `metrics` con las cuatro métricas de `services/telemetry/analysis.py`, llamadas con
el mismo período. Es JSON puro: lo guarda el backend de resultados y lo devuelve `GET /tasks/{task_id}`.

La API ya validó y resolvió el período antes de encolar (decisión T6), así que aquí solo se interpreta. Una
fecha mal formada o un período al revés es un error de programación, permanente.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from brasaland_telemetry.analysis import (
    api_latency_by_route,
    auth_failure_rate,
    error_rate_by_type,
    events_per_day,
)
from sqlalchemy.engine import Connection


class InvalidReportPeriod(ValueError):
    """El período recibido no es válido (la API debió rechazarlo antes de encolar)."""


def parse_utc(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise InvalidReportPeriod(f"`{name}` no es una fecha ISO 8601: {value!r}.") from error
    if parsed.tzinfo is None:
        raise InvalidReportPeriod(f"`{name}` debe llevar zona horaria (UTC): {value!r}.")
    return parsed.astimezone(UTC)


def resolve(start: str, end: str) -> tuple[datetime, datetime]:
    start_at, end_at = parse_utc(start, "start"), parse_utc(end, "end")
    if start_at >= end_at:
        raise InvalidReportPeriod("`start` debe ser anterior a `end`.")
    return start_at, end_at


def iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def build_report(connection: Connection, start: datetime, end: datetime) -> dict[str, Any]:
    return {
        "period": {"from": iso_utc(start), "to": iso_utc(end)},
        "metrics": {
            "events_per_day": events_per_day(connection, start, end),
            "error_rate_by_type": error_rate_by_type(connection, start, end),
            "api_latency_by_route": api_latency_by_route(connection, start, end),
            "auth_failure_rate": auth_failure_rate(connection, start, end),
        },
    }
