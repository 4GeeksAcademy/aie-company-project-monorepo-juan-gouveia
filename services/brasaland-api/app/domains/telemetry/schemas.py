"""Schemas del receptor de telemetría.

`TelemetryEvent` es el Event Envelope del plan (`docs/telemetry/telemetry-plan.md`, sección 7, y
`definitions/envelope` de `docs/telemetry/event-schemas.json`). Los campos llevan exactamente los
nombres del enunciado (`eventId`, `sessionId`… en camelCase y `event_type` en snake_case), más los dos
que añade el plan (`source` y `environment`). Ningún campo puede faltar: cuando un dato no aplica, su
valor es `null`. El modelo no admite campos extra.

En la fase de almacenamiento, `TelemetryEvent` se reutiliza sin cambios como validador de cada evento
del lote (`TelemetryEvent.model_validate`), no como tipo del cuerpo. El contenido de `properties` lo
comprueba después el receptor contra el catálogo generado desde `event-schemas.json` (`catalog.py`).
"""

import re
import datetime as dt
from typing import Annotated, Any, Literal

from pydantic import UUID4, AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator

# Lote: lo que envía el backoffice cada 10 s o al llegar a 20 eventos. El máximo deja margen para los
# lotes de reintento y de sendBeacon sin aceptar cuerpos arbitrariamente grandes.
MAX_BATCH_EVENTS = 100

# ISO 8601 en UTC con milisegundos, como fija el envelope: 2026-11-18T17:36:46.123Z
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

EventType = Annotated[str, StringConstraints(pattern=r"^[a-z]+(_[a-z]+)+$", max_length=64)]
SchemaVersion = Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", max_length=20)]


class TelemetryEvent(BaseModel):
    """Un evento de telemetría con el envelope estándar de Brasaland."""

    model_config = ConfigDict(extra="forbid")

    eventId: UUID4 = Field(description="Identificador único del evento (UUID v4), generado por el emisor al capturarlo")
    timestamp: AwareDatetime = Field(
        description="Momento del hecho en ISO 8601, UTC y con milisegundos (`2026-11-18T17:36:46.123Z`); no el del envío"
    )
    sessionId: UUID4 | None = Field(description="Sesión del navegador (UUID v4 creado al iniciar sesión); `null` sin sesión")
    userId: UUID4 | None = Field(description="UUID de la cuenta (seudónimo, nunca el email); `null` sin usuario autenticado")
    event_type: EventType = Field(description="Tipo de evento, `entidad_acción` en snake_case (p. ej. `inbound_order_created`)")
    schemaVersion: SchemaVersion = Field(description="Versión SemVer del esquema de ese evento (p. ej. `1.0.0`)")
    requestId: UUID4 | None = Field(
        description="Id de la petición a la API que originó el evento (`X-Request-Id`); `null` si no nace de una petición"
    )
    properties: dict[str, Any] = Field(description="Datos propios del evento: solo las claves del allowlist de su esquema")
    source: Literal["api", "bff", "browser", "process"] = Field(description="Emisor del evento")
    environment: Literal["development", "staging", "production"] = Field(description="Entorno de origen del evento")

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_in_envelope_format(cls, value: Any) -> Any:
        # Pydantic aceptaría otras variantes de ISO 8601 (sin milisegundos, con +02:00…); el envelope
        # fija una sola para que todos los emisores sean comparables.
        if not isinstance(value, str) or not TIMESTAMP_PATTERN.match(value):
            raise ValueError("debe ser ISO 8601 en UTC con milisegundos, como 2026-11-18T17:36:46.123Z")
        return value


class TelemetryBatch(BaseModel):
    """Cuerpo de `POST /telemetry/events`: un lote de eventos, leído de forma laxa.

    Cada elemento de `events` llega sin validar: el receptor lo valida por separado con
    `TelemetryEvent.model_validate`, para que un evento inválido no haga fallar el lote entero (plan de
    telemetría, sección 14.3). Las claves que acompañen a `events` se ignoran. El máximo de
    `MAX_BATCH_EVENTS` lo comprueba el receptor, con su propio código de error.
    """

    model_config = ConfigDict(extra="ignore")

    events: list[Any] = Field(description=f"Hasta {MAX_BATCH_EVENTS} eventos; cada uno se valida por separado")


class TelemetryReceipt(BaseModel):
    """Respuesta de `POST /telemetry/events`: `received` = `stored` + `rejected`."""

    received: int = Field(ge=0, description="Cantidad de eventos del lote")
    stored: int = Field(
        ge=0, description="Eventos válidos guardados; incluye los repetidos, que ya estaban guardados por su eventId"
    )
    rejected: int = Field(ge=0, description="Eventos que no cumplen el contrato; no se guardan")


# --- Reporte técnico (POST /telemetry/report, plan de telemetría, sección 16; ticket #DEV-55) -------------


class TelemetryReportRequest(BaseModel):
    """Cuerpo de `POST /telemetry/report`. Las dos fechas son opcionales; sin cuerpo, los últimos 7 días."""

    model_config = ConfigDict(extra="forbid")

    start_date: str | None = Field(
        None, description="Inicio inclusivo, ISO 8601 (`2026-11-14` o `2026-11-14T08:00:00Z`); sin zona = UTC"
    )
    end_date: str | None = Field(None, description="Fin exclusivo, ISO 8601; por defecto, ahora")


# Contrato del resultado de la tarea `telemetry.report` (`services/tasks/report.py`), el `result` de
# `GET /tasks/{task_id}` con `success`. El worker no depende de la API: la prueba de contrato
# (`tests/telemetry/test_report_task_contract.py`) valida con estos modelos el informe que arma.

Rate = Annotated[float, Field(ge=0, le=1, description="Fracción de 0 a 1, con 4 decimales")]


class ReportPeriod(BaseModel):
    """Ventana del reporte, `[from, to)` en UTC: inicio inclusivo, fin exclusivo."""

    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from", description="Inicio inclusivo, ISO 8601 en UTC (`2026-11-13T10:00:00Z`)")
    to: str = Field(description="Fin exclusivo, ISO 8601 en UTC")


class EventsPerDay(BaseModel):
    """Volumen de un día, por nivel."""

    date: dt.date = Field(description="Día UTC")
    total: int = Field(ge=0, description="Eventos del día")
    info: int = Field(ge=0)
    warn: int = Field(ge=0)
    error: int = Field(ge=0)


class ErrorRateByType(BaseModel):
    """Peso de un tipo de fallo (`warn` o `error`) sobre el volumen de su día."""

    date: dt.date = Field(description="Día UTC")
    event_type: str
    level: Literal["warn", "error"]
    count: int = Field(ge=1, description="Eventos de ese tipo en el día")
    rate: Rate


class ApiLatencyByRoute(BaseModel):
    """Latencia de una ruta de la API en un día, a partir de `api_latency_recorded`."""

    date: dt.date = Field(description="Día UTC")
    method: str
    route: str = Field(description="Plantilla de la ruta, sin ids reales")
    samples: int = Field(ge=1, description="Eventos de latencia (muestreados)")
    avg_ms: float = Field(ge=0, description="Media en ms, ponderada por 1/sample_rate")
    max_ms: float = Field(ge=0, description="Máximo observado en ms")


class AuthFailureRate(BaseModel):
    """Intentos de login de un día y la fracción que falló."""

    date: dt.date = Field(description="Día UTC")
    attempts: int = Field(ge=1, description="login_failed + login_succeeded")
    failed: int = Field(ge=0, description="login_failed")
    failure_rate: Rate


class ReportMetrics(BaseModel):
    """Una lista de filas por métrica, todas agrupadas por día UTC."""

    events_per_day: list[EventsPerDay]
    error_rate_by_type: list[ErrorRateByType]
    api_latency_by_route: list[ApiLatencyByRoute]
    auth_failure_rate: list[AuthFailureRate]


class TelemetryReport(BaseModel):
    """El informe técnico: resultado de `telemetry.report` (antes, la respuesta de `GET /telemetry/report`)."""

    period: ReportPeriod
    metrics: ReportMetrics
