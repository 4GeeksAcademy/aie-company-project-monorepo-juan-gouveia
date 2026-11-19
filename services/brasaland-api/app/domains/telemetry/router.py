"""Receptor provisional de telemetría: `POST /telemetry/events`.

Es un stub de verificación de la fase de captura. Valida el formato del lote con `TelemetryBatch`
(el envelope de cada evento con `TelemetryEvent`), registra en el log cuántos eventos llegaron y el
`event_type` de cada uno, y responde `{"received": N}`. No guarda nada: el almacenamiento es la fase
siguiente, que sustituirá el cuerpo de esta ruta sin cambiar su contrato.

Decisiones (plan de telemetría, sección 13.3):
- Fuera de `/api/v1` y pública, como `/health`: la recepción de telemetría es una vía de entrada
  aparte, no un recurso versionado del negocio, y `navigator.sendBeacon` no puede enviar
  `Authorization`. El CORS de `main.py` solo admite el origen del backoffice.
- Acepta el cuerpo como `application/json` (envíos con `fetch`) y como `text/plain` (`sendBeacon`, que
  no puede enviar JSON a otro origen sin una comprobación previa de CORS). En los dos casos se
  interpreta como JSON.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute

from app.core.errors import ApiError
from app.core.logs import console_logger
from app.domains.telemetry.schemas import MAX_BATCH_EVENTS, TelemetryBatch, TelemetryReceipt

# Un lote de 100 eventos ocupa unos 100 KB; sendBeacon admite 64 KB. Más que esto no es un lote legítimo.
MAX_BODY_BYTES = 256 * 1024

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


@router.post(
    "/events",
    response_model=TelemetryReceipt,
    summary="Recibir un lote de eventos de telemetría (stub)",
    description=(
        f"Valida un lote de 1 a {MAX_BATCH_EVENTS} eventos con el envelope estándar y responde cuántos llegaron. "
        "No guarda nada todavía. Acepta el cuerpo como `application/json` o como `text/plain` (sendBeacon)."
    ),
)
def receive_events(batch: TelemetryBatch) -> TelemetryReceipt:
    event_types = ", ".join(event.event_type for event in batch.events)
    logger.info(f"Lote de telemetría recibido: {len(batch.events)} eventos | {event_types}")
    return TelemetryReceipt(received=len(batch.events))
