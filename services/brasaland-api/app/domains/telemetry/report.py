"""Reporte técnico de telemetría: período, cache y llamada al pipeline (plan de telemetría, sección 16.3).

El endpoint no calcula nada: resuelve el período **una vez** y llama a las funciones de métrica de
`services/telemetry/analysis.py` (`brasaland_telemetry.analysis`), que lo aplican en SQL. El resultado
se guarda ya serializado en una cache en memoria de 60 s.

**Clave de la cache.** Son los parámetros tal como llegan, normalizados a UTC, con `now` para el que
falte, no el período resuelto: sin parámetros, el fin es "ahora" y cambiaría en cada petición, así que
la cache nunca acertaría. El período se resuelve dentro del cálculo y se guarda con el resultado: dos
peticiones sin parámetros dentro del TTL reciben el mismo JSON, con el mismo `period`.

La cache no se invalida al llegar eventos nuevos: el reporte puede ir hasta 60 s por detrás de la tabla,
que para una vista técnica es aceptable. Es la misma para todos los administradores (el reporte no
depende de quién lo pide).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pandas.errors import DatabaseError as PandasDatabaseError
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.core.cache import TTLCache
from app.core.errors import ApiError
from app.domains.telemetry.schemas import ReportMetrics, ReportPeriod, TelemetryReport
from brasaland_telemetry.analysis import api_latency_by_route, auth_failure_rate, error_rate_by_type, events_per_day

DEFAULT_WINDOW = timedelta(days=7)
MAX_WINDOW = timedelta(days=90)
CACHE_TTL_SECONDS = 60
NOW = "now"

report_cache: TTLCache[bytes] = TTLCache(CACHE_TTL_SECONDS)


class TelemetryReportUnavailable(Exception):
    """La base no pudo responder a las consultas del reporte."""

    def __init__(self, reason: str, missing_table: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.missing_table = missing_table


@dataclass(frozen=True)
class ReportRequest:
    """Los parámetros recibidos, ya en UTC; `None` es "no se pasó"."""

    start: datetime | None
    end: datetime | None

    @property
    def cache_key(self) -> str:
        return f"{_key_part(self.start)}|{_key_part(self.end)}"


def _key_part(value: datetime | None) -> str:
    return value.isoformat() if value else NOW


def utc_now() -> datetime:
    """Ahora, en UTC y sin microsegundos: así `period.to` es exactamente el límite usado en SQL."""
    return datetime.now(UTC).replace(microsecond=0)


def parse_instant(raw: str | None, name: str) -> datetime | None:
    """Un parámetro de fecha en ISO 8601, en UTC. Vacío o ausente → None.

    Admite fecha sola (`2026-11-14`, las 00:00 UTC) y fecha y hora, con zona (`Z` o `+02:00`) o sin ella
    (se toma como UTC). Un `+` sin codificar en la URL llega como espacio: se restaura.
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


def _iso(value: datetime) -> str:
    text = value.astimezone(UTC).isoformat()
    return text.replace("+00:00", "Z")


def _unavailable(error: Exception) -> TelemetryReportUnavailable:
    """Resume el error de la base sin el SQL: solo el tipo y la primera línea del error del driver."""
    # pandas envuelve a veces el error de SQLAlchemy; el del driver está en `orig`.
    cause = error.__cause__ if isinstance(error, PandasDatabaseError) and error.__cause__ else error
    driver_error = getattr(cause, "orig", None) or cause
    detail = str(driver_error).strip()
    first_line = detail.splitlines()[0] if detail else "sin detalle"
    lowered = detail.lower()
    missing_table = "telemetry_events" in lowered and ("does not exist" in lowered or "no such table" in lowered)
    return TelemetryReportUnavailable(f"{type(driver_error).__name__}: {first_line}", missing_table)


def build_report(connection: Connection, start: datetime, end: datetime) -> TelemetryReport:
    """Llama a cada función de métrica con el mismo período y junta los resultados."""
    try:
        metrics = ReportMetrics(
            events_per_day=events_per_day(connection, start, end),
            error_rate_by_type=error_rate_by_type(connection, start, end),
            api_latency_by_route=api_latency_by_route(connection, start, end),
            auth_failure_rate=auth_failure_rate(connection, start, end),
        )
    except (SQLAlchemyError, PandasDatabaseError) as error:
        raise _unavailable(error) from error
    return TelemetryReport(period=ReportPeriod(**{"from": _iso(start), "to": _iso(end)}), metrics=metrics)


def get_report(
    request: ReportRequest,
    connect: Callable[[], Connection],
    now: Callable[[], datetime] | None = None,
) -> tuple[bytes, bool]:
    """El reporte serializado y si salió de la cache. Un error no se guarda en la cache."""

    def load() -> bytes:
        start, end = resolve_period(request, (now or utc_now)())
        report = build_report(connect(), start, end)
        return report.model_dump_json(by_alias=True).encode()

    return report_cache.get_or_load(request.cache_key, load)
