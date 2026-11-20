"""Receptor de telemetría: `POST /telemetry/events` (plan de telemetría, sección 14.3).

Lee el lote de forma laxa (`{"events": [...]}`, cada elemento sin validar), valida cada evento por
separado, guarda los válidos en `telemetry_events` con un solo INSERT y responde
`{"received", "stored", "rejected"}`. Un evento inválido se rechaza solo: el resto del lote se guarda
igual. La URL y el formato del lote son los de la fase de captura, así que el backoffice no cambia.

Decisiones:
- Fuera de `/api/v1` y pública, como `/health`: la recepción de telemetría es una vía de entrada
  aparte, no un recurso versionado del negocio, y `navigator.sendBeacon` no puede enviar
  `Authorization`. El CORS de `main.py` solo admite el origen del backoffice (sección 13.3).
- Acepta el cuerpo como `application/json` (envíos con `fetch`) y como `text/plain` (`sendBeacon`, que
  no puede enviar JSON a otro origen sin una comprobación previa de CORS). En los dos casos se
  interpreta como JSON.
- Respuestas: 200 mientras el lote tenga una lista `events` (aunque se rechacen todos); 422 si no la
  tiene o trae más de `MAX_BATCH_EVENTS`; 413 por encima de 256 KB; 503 si la base no puede guardar,
  para que el backoffice reintente (los reintentos no duplican filas).
- El log nunca copia valores de los eventos: solo cantidades, tipos y el campo que falló.

`GET /telemetry/report` (fase de reporte técnico, sección 16.3) sirve las métricas del pipeline de
`services/telemetry/analysis.py` con una cache de 60 s (`report.py`). Al contrario que el receptor,
exige token y rol `admin`: describe el estado interno del sistema. El backoffice lo pide por una ruta
propia de su intermediario; el CORS de `/telemetry` sigue limitado a `POST`.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.routing import APIRoute
from sqlmodel import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.logs import console_logger
from app.domains.auth.dependencies import require_admin
from app.domains.telemetry.report import (
    MAX_WINDOW,
    ReportRequest,
    TelemetryReportUnavailable,
    get_report,
    parse_instant,
)
from app.domains.telemetry.schemas import MAX_BATCH_EVENTS, TelemetryBatch, TelemetryReceipt, TelemetryReport
from app.domains.telemetry.service import ParsedBatch, TelemetryStorageError, parse_batch, store_events

# Un lote de 100 eventos ocupa unos 100 KB; sendBeacon admite 64 KB. Más que esto no es un lote legítimo.
MAX_BODY_BYTES = 256 * 1024
# Rechazos que se detallan en la línea de log de un lote; del resto solo cuenta la cantidad.
MAX_LOGGED_REJECTIONS = 10

logger = console_logger("api.telemetry")


class TelemetryRoute(APIRoute):
    """Ruta que lee como JSON un cuerpo `text/plain` y rechaza los cuerpos demasiado grandes."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            content_type = request.headers.get("content-type", "")
            if content_type.split(";")[0].strip().lower() == "text/plain":
                headers = [(name, value) for name, value in request.scope["headers"] if name != b"content-type"]
                headers.append((b"content-type", b"application/json"))
                request = Request({**request.scope, "headers": headers}, request.receive)
            # body() queda guardado en el objeto Request: el handler lo vuelve a leer sin consumir nada.
            if len(await request.body()) > MAX_BODY_BYTES:
                raise ApiError(413, "batch_too_large", "El lote de telemetría es demasiado grande.")
            return await handler(request)

        return route_handler


router = APIRouter(prefix="/telemetry", tags=["telemetry"], route_class=TelemetryRoute)


def _log_batch(received: int, stored: int, inserted: int, parsed: ParsedBatch) -> None:
    repeated = stored - inserted
    line = f"Lote de telemetría: {received} recibidos, {stored} guardados"
    if repeated:
        line += f" ({repeated} repetidos)"
    line += f", {len(parsed.rejections)} rechazados"
    if parsed.valid:
        line += " | " + ", ".join(event.event_type for event in parsed.valid)
    if parsed.rejections:
        details = [rejection.describe() for rejection in parsed.rejections[:MAX_LOGGED_REJECTIONS]]
        if len(parsed.rejections) > MAX_LOGGED_REJECTIONS:
            details.append(f"y {len(parsed.rejections) - MAX_LOGGED_REJECTIONS} más")
        line += " | rechazos: " + "; ".join(details)
    (logger.warning if parsed.rejections else logger.info)(line)


@router.post(
    "/events",
    response_model=TelemetryReceipt,
    summary="Recibir y guardar un lote de eventos de telemetría",
    description=(
        f"Valida por separado cada evento de un lote de hasta {MAX_BATCH_EVENTS} (envelope estándar y "
        "allowlist de su esquema), guarda los válidos en `telemetry_events` con un solo INSERT y responde "
        "cuántos llegaron, cuántos se guardaron y cuántos se rechazaron. Un evento inválido no hace fallar "
        "el lote. Acepta el cuerpo como `application/json` o como `text/plain` (sendBeacon)."
    ),
    responses={
        413: {"description": "El cuerpo pasa de 256 KB (`batch_too_large`)."},
        422: {"description": "El cuerpo no tiene una lista `events` o trae demasiados eventos (`too_many_events`)."},
        503: {"description": "La base de datos no pudo guardar el lote (`telemetry_storage_unavailable`)."},
    },
)
def receive_events(batch: TelemetryBatch, session: Session = Depends(get_db)) -> TelemetryReceipt:
    received = len(batch.events)
    if received > MAX_BATCH_EVENTS:
        raise ApiError(422, "too_many_events", f"Un lote admite como máximo {MAX_BATCH_EVENTS} eventos.")

    parsed = parse_batch(batch.events)
    try:
        inserted = store_events(session, parsed.valid)
    except TelemetryStorageError as error:
        if error.missing_table:
            logger.error(
                "No se pudo guardar el lote de telemetría: falta la tabla telemetry_events. "
                "Ejecuta services/brasaland-api/migrations/002_telemetry_events.sql en Supabase."
            )
        else:
            logger.error(f"No se pudo guardar el lote de telemetría ({received} eventos): {error.reason}")
        raise ApiError(
            503, "telemetry_storage_unavailable", "No se pudieron guardar los eventos. Vuelve a intentarlo."
        ) from error

    stored = len(parsed.valid)
    _log_batch(received, stored, inserted, parsed)
    return TelemetryReceipt(received=received, stored=stored, rejected=len(parsed.rejections))


@router.get(
    "/report",
    response_model=TelemetryReport,
    summary="Reporte técnico de telemetría",
    description=(
        "Métricas operacionales por día UTC calculadas sobre `telemetry_events`: volumen por nivel "
        "(`events_per_day`), peso de cada tipo de fallo (`error_rate_by_type`), latencia de la API por método "
        "y ruta (`api_latency_by_route`) y tasa de fallos de login (`auth_failure_rate`). Sin parámetros, "
        "los últimos 7 días hasta ahora. El resultado se guarda 60 s por combinación de parámetros "
        f"(`X-Cache: HIT` o `MISS`). Solo administradores. Período máximo: {MAX_WINDOW.days} días."
    ),
    responses={
        200: {"headers": {"X-Cache": {"description": "`HIT` si salió de la cache; `MISS` si se calculó"}}},
        401: {"description": "Sin token o con un token no válido."},
        403: {"description": "El usuario no es administrador."},
        422: {"description": "Fecha mal formada (`invalid_date`), inicio no anterior al fin (`invalid_period`) o "
              f"más de {MAX_WINDOW.days} días (`period_too_long`)."},
        503: {"description": "La base de datos no pudo responder (`telemetry_report_unavailable`)."},
    },
)
def get_telemetry_report(
    start_date: str | None = Query(
        None, description="Inicio inclusivo, ISO 8601 (`2026-11-14` o `2026-11-14T08:00:00Z`); sin zona = UTC"
    ),
    end_date: str | None = Query(None, description="Fin exclusivo, ISO 8601; por defecto, ahora"),
    session: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> Response:
    request = ReportRequest(start=parse_instant(start_date, "start_date"), end=parse_instant(end_date, "end_date"))
    try:
        body, hit = get_report(request, session.connection)
    except TelemetryReportUnavailable as error:
        if error.missing_table:
            logger.error(
                "No se pudo calcular el reporte de telemetría: falta la tabla telemetry_events. "
                "Ejecuta services/brasaland-api/migrations/002_telemetry_events.sql en Supabase."
            )
        else:
            logger.error(f"No se pudo calcular el reporte de telemetría: {error.reason}")
        raise ApiError(
            503, "telemetry_report_unavailable", "No se pudo calcular el reporte de telemetría. Vuelve a intentarlo."
        ) from error
    return Response(content=body, media_type="application/json", headers={"X-Cache": "HIT" if hit else "MISS"})
