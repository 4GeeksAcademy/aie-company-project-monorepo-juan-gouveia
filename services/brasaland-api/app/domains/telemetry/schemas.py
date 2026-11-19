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
