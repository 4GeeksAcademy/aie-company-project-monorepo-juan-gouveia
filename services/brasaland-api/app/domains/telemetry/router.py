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

`POST /telemetry/report` (fase de reporte técnico, sección 16.3; ticket #DEV-55) ya no calcula el
informe: valida el período, encola la tarea `telemetry.report` y responde `202 {"task_id"}` al momento.
El worker (`services/tasks`) calcula las métricas de `services/telemetry/analysis.py`, y el resultado se
consulta en `GET /tasks/{task_id}`. Es `POST` y no `GET`, como antes, porque crea trabajo (decisión T2).
La misma petición con su tarea viva, o hasta 60 s después de terminar bien, devuelve el mismo `task_id`
(T14). Al contrario que el receptor, exige token y rol `admin`: describe el estado interno del sistema.
El backoffice lo pide por una ruta propia de su intermediario, no desde el navegador.
"""

from collections.abc import Callable, Coroutine
from typing import Any

# Nombre registrado de la tarea en el worker: se encola por nombre, sin importar su código.
# `brasaland_tasks.names` no crea la aplicación de Celery al importarse (no exige REDIS_URL).
from brasaland_tasks.names import TELEMETRY_REPORT_TASK
from fastapi import APIRouter, Depends, Request, Response
from fastapi.routing import APIRoute
from sqlmodel import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.logs import console_logger
from app.domains.auth.dependencies import require_admin
from app.domains.tasks.dependencies import get_task_queue, queue_unavailable
from app.domains.tasks.queue import TaskQueue, TaskQueueUnavailable
from app.domains.tasks.schemas import TaskAccepted
from app.domains.telemetry.report import MAX_WINDOW, ReportRequest, parse_instant, resolve_period, task_kwargs, utc_now
from app.domains.telemetry.schemas import MAX_BATCH_EVENTS, TelemetryBatch, TelemetryReceipt, TelemetryReportRequest
from app.domains.telemetry.service import ParsedBatch, TelemetryStorageError, parse_batch, store_events
from app.domains.users.models import User

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


@router.post(
    "/report",
    status_code=202,
    response_model=TaskAccepted,
    summary="Encolar el reporte técnico de telemetría",
    description=(
        "Encola el cálculo de las métricas operacionales por día UTC sobre `telemetry_events` (volumen por "
        "nivel, peso de cada tipo de fallo, latencia de la API por método y ruta y tasa de fallos de login) y "
        "responde al momento con el `task_id`. El informe se consulta en `GET /tasks/{task_id}`. Sin fechas, "
        "los últimos 7 días hasta ahora. La misma petición con su tarea en cola o en curso, o hasta 60 s "
        "después de terminar bien, devuelve el mismo `task_id`. Solo administradores. Período máximo: "
        f"{MAX_WINDOW.days} días."
    ),
    responses={
        202: {"headers": {"Location": {"description": "`/tasks/{task_id}`, donde se consulta el estado"}}},
        401: {"description": "Sin token o con un token no válido."},
        403: {"description": "El usuario no es administrador."},
        422: {"description": "Fecha mal formada (`invalid_date`), inicio no anterior al fin (`invalid_period`) o "
              f"más de {MAX_WINDOW.days} días (`period_too_long`)."},
        503: {"description": "La cola de tareas no está disponible (`task_queue_unavailable`)."},
    },
)
def request_telemetry_report(
    response: Response,
    body: TelemetryReportRequest | None = None,
    admin: User = Depends(require_admin),
    queue: TaskQueue = Depends(get_task_queue),
) -> TaskAccepted:
    body = body or TelemetryReportRequest()
    request = ReportRequest(
        start=parse_instant(body.start_date, "start_date"), end=parse_instant(body.end_date, "end_date")
    )
    start, end = resolve_period(request, utc_now())
    try:
        task_id = queue.submit(
            TELEMETRY_REPORT_TASK, task_kwargs(start, end, admin.id), owner_id=admin.id, dedupe_key=request.dedupe_key
        )
    except TaskQueueUnavailable as error:
        logger.error(f"No se pudo encolar el reporte de telemetría: {error}")
        raise queue_unavailable() from error
    response.headers["Location"] = f"/tasks/{task_id}"
    return TaskAccepted(task_id=task_id)
