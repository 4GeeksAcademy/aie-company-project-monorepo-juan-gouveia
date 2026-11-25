"""Reporte técnico de telemetría: el período que se encola (plan de telemetría, sección 16.3; #DEV-55).

La API ya no calcula el informe: valida y resuelve el período **una vez** y encola la tarea
`telemetry.report` (`services/tasks`), que llama a las funciones de `services/telemetry/analysis.py` con
ese período. Las fechas se validan aquí, antes de encolar (decisión T6): una fecha mal formada es un 422
inmediato, no una tarea fallida.

**Clave de deduplicación** (T2 y T14). Son los parámetros tal como llegan, normalizados a UTC, con `now`
para el que falte, no el período resuelto: sin parámetros, el fin es "ahora" y cambiaría en cada petición,
así que nunca coincidiría. Dos peticiones sin parámetros con la tarea viva, o hasta 60 s después de que
termine bien, reciben el mismo `task_id` y el mismo `period`. Es la clave de la antigua caché en memoria,
ahora compartida entre procesos en Redis.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.errors import ApiError

DEFAULT_WINDOW = timedelta(days=7)
MAX_WINDOW = timedelta(days=90)
NOW = "now"


@dataclass(frozen=True)
class ReportRequest:
    """Los parámetros recibidos, ya en UTC; `None` es "no se pasó"."""

    start: datetime | None
    end: datetime | None

    @property
    def dedupe_key(self) -> str:
        return f"{_key_part(self.start)}|{_key_part(self.end)}"


def _key_part(value: datetime | None) -> str:
    return value.isoformat() if value else NOW


def utc_now() -> datetime:
    """Ahora, en UTC y sin microsegundos: así `period.to` es exactamente el límite usado en SQL."""
    return datetime.now(UTC).replace(microsecond=0)


def parse_instant(raw: str | None, name: str) -> datetime | None:
    """Un parámetro de fecha en ISO 8601, en UTC. Vacío o ausente → None.

    Admite fecha sola (`2026-11-14`, las 00:00 UTC) y fecha y hora, con zona (`Z` o `+02:00`) o sin ella
    (se toma como UTC). Un `+` sin codificar en una URL llega como espacio: se restaura.
    """
    if raw is None or not raw.strip():
        return None
    text = raw.strip()
    if "T" in text and " " in text:
        text = text.replace(" ", "+")
    try:
        value = datetime.fromisoformat(text)
    except ValueError as error:
        raise ApiError(
            422,
            "invalid_date",
            f"`{name}` debe ser una fecha ISO 8601, por ejemplo 2026-11-14 o 2026-11-14T08:00:00Z.",
        ) from error
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def resolve_period(request: ReportRequest, now: datetime) -> tuple[datetime, datetime]:
    """El período `[start, end)`: por defecto, los 7 días anteriores a `now`.

    Solo `end_date` → los 7 días anteriores a él; solo `start_date` → hasta ahora.
    """
    end = request.end or now
    start = request.start or end - DEFAULT_WINDOW
    if start >= end:
        raise ApiError(422, "invalid_period", "`start_date` debe ser anterior a `end_date`.")
    if end - start > MAX_WINDOW:
        raise ApiError(422, "period_too_long", f"El período no puede pasar de {MAX_WINDOW.days} días.")
    return start, end


def task_kwargs(start: datetime, end: datetime, requested_by: str) -> dict[str, str]:
    """Los argumentos de `telemetry.report`: solo referencias (dos fechas ISO 8601 UTC y un id)."""
    return {
        "start": start.astimezone(UTC).isoformat(),
        "end": end.astimezone(UTC).isoformat(),
        "requested_by": requested_by,
    }
