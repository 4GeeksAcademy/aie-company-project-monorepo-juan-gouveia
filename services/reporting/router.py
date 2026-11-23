"""Endpoints del Reporte Semanal de Costo y Merma por Local (diseño, §6; briefing del pipeline, §6).

Tres rutas, literales del briefing y fuera de `/api/v1`, como las de telemetría:

- `GET /reporting/weekly-location-performance`: las filas de KPIs de una semana (el feed del dashboard).
- `GET /reporting/pipeline-runs/latest`: estado y metadata de la última corrida.
- `POST /reporting/pipeline-runs`: pide una corrida manual a Prefect y responde 202.

Aquí solo hay HTTP: autenticación, validación de parámetros y serialización. La lectura de `reporting.*`
y el disparo vienen de `data/pipelines` (`brasaland_pipelines.repository` y `.trigger`); ninguna lógica del
pipeline se repite aquí. Se monta en la API (`app.main`) y usa sus convenciones: `ApiError` con el formato
`{"error": {"code", "message"}}`, sus dependencias de autenticación y su caché en memoria.
"""

from datetime import date
from uuid import UUID

from app.core.cache import TTLCache
from app.core.database import get_db, get_engine
from app.core.errors import ApiError
from app.core.logs import console_logger
from app.domains.auth.dependencies import require_admin, require_manager_or_admin
from app.domains.users.models import User
from brasaland_pipelines import repository, trigger
from brasaland_reporting.schemas import (
    PipelineRunRead,
    PipelineRunRequest,
    WeeklyLocationPerformance,
)
from fastapi import APIRouter, Body, Depends, Query, Response, status
from sqlalchemy.exc import DBAPIError
from sqlmodel import Session

logger = console_logger("api.reporting")
router = APIRouter(prefix="/reporting", tags=["reporting"])

# Los KPIs cambian una vez por semana (o tras una corrida manual, en otro proceso que no puede
# invalidar esta caché): 5 minutos por semana pedida. Tras una corrida, el dato nuevo se ve en 5 min.
WEEKLY_CACHE_TTL_SECONDS = 300
weekly_cache: TTLCache[bytes] = TTLCache(WEEKLY_CACHE_TTL_SECONDS)

READERS = "Solo administradores y gerentes (`admin`, `manager`)."
MISSING_TABLES = ("does not exist", "no such table")


class _WeekNotComputed(Exception):
    """La semana pedida (o ninguna) está calculada. No se guarda en la caché."""


def _unavailable(error: DBAPIError, what: str) -> ApiError:
    """503 `reporting_unavailable`; si faltan las tablas, el log dice qué migración ejecutar."""
    if any(marker in str(error.orig) for marker in MISSING_TABLES):
        logger.error(f"No se pudo leer {what}: faltan las tablas de reporting. Ejecuta migrations/005_reporting.sql en Supabase.")
    else:
        logger.error(f"No se pudo leer {what}: {type(error.orig).__name__}")
    return ApiError(503, "reporting_unavailable", "No se pudo consultar el reporte de negocio. Vuelve a intentarlo.")


@router.get(
    "/weekly-location-performance",
    response_model=WeeklyLocationPerformance,
    summary="KPIs semanales por local",
    description=(
        "Reporte Semanal de Costo y Merma por Local: costo de compra, costo de merma, ratio de merma, quiebres de "
        "stock y alertas de subida de precio de cada local en una semana ISO, en la moneda del local. Sin "
        "`week_start`, la semana calculada más reciente. La respuesta se guarda 5 minutos por semana "
        f"(`X-Cache: HIT` o `MISS`). {READERS}"
    ),
    responses={
        200: {"headers": {"X-Cache": {"description": "`HIT` si salió de la cache; `MISS` si se leyó de la base"}}},
        401: {"description": "Sin token o con un token no válido."},
        403: {"description": "El usuario no es administrador ni gerente."},
        404: {"description": "Esa semana (o ninguna) está calculada (`week_not_computed`)."},
        422: {"description": "`week_start` mal formada o que no es lunes (`invalid_week_start`)."},
        503: {"description": "La base no respondió o faltan las tablas de reporting (`reporting_unavailable`)."},
    },
)
def get_weekly_location_performance(
    week_start: date | None = Query(None, description="Lunes de la semana ISO (`YYYY-MM-DD`); por defecto, la más reciente calculada"),
    session: Session = Depends(get_db),
    _reader: User = Depends(require_manager_or_admin),
) -> Response:
    if week_start is not None and week_start.weekday() != 0:
        raise ApiError(
            422,
            "invalid_week_start",
            "week_start debe ser un lunes (el inicio de la semana ISO).",
            details=[{"field": "week_start", "message": "Debe ser un lunes."}],
        )

    def load() -> bytes:
        try:
            found = repository.read_weekly_location_performance(session.connection(), week_start)
        except DBAPIError as error:
            raise _unavailable(error, "el reporte semanal") from error
        if found is None:
            raise _WeekNotComputed
        week, rows = found
        return WeeklyLocationPerformance(week_start=week, locations=rows).model_dump_json().encode()

    try:
        body, hit = weekly_cache.get_or_load(week_start.isoformat() if week_start else "latest", load)
    except _WeekNotComputed:
        message = f"La semana {week_start} no está calculada." if week_start else "Todavía no hay ninguna semana calculada."
        raise ApiError(404, "week_not_computed", message) from None
    return Response(content=body, media_type="application/json", headers={"X-Cache": "HIT" if hit else "MISS"})


@router.get(
    "/pipeline-runs/latest",
    response_model=PipelineRunRead,
    summary="Última corrida del pipeline",
    description=(
        "Estado y metadata de la última corrida del pipeline del reporte semanal (`reporting.pipeline_runs`): "
        "rango de semanas, horas de inicio y fin, eventos leídos, rechazados y descartados, filas escritas y "
        f"error. Sin cache: sirve para seguir una corrida. {READERS}"
    ),
    responses={
        401: {"description": "Sin token o con un token no válido."},
        403: {"description": "El usuario no es administrador ni gerente."},
        404: {"description": "El pipeline nunca corrió (`no_pipeline_runs`)."},
        503: {"description": "La base no respondió o faltan las tablas de reporting (`reporting_unavailable`)."},
    },
)
def get_latest_pipeline_run(
    session: Session = Depends(get_db),
    _reader: User = Depends(require_manager_or_admin),
) -> PipelineRunRead:
    try:
        run = repository.read_latest_pipeline_run(session.connection())
    except DBAPIError as error:
        raise _unavailable(error, "la última corrida") from error
    if run is None:
        raise ApiError(404, "no_pipeline_runs", "El pipeline todavía no ha corrido.")
    return PipelineRunRead.model_validate(run)


@router.post(
    "/pipeline-runs",
    response_model=PipelineRunRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Disparar una corrida manual",
    description=(
        "Registra una corrida en `pending` y la pone en la cola de Prefect (deployment "
        "`weekly-location-performance/weekly`), sin esperar a que termine: se sigue con "
        "`GET /reporting/pipeline-runs/latest`. Sin cuerpo, recalcula las 4 últimas semanas cerradas; con "
        "`week_from` y `week_to`, un backfill de hasta 26 semanas, sin la semana en curso. Solo administradores."
    ),
    responses={
        401: {"description": "Sin token o con un token no válido."},
        403: {"description": "El usuario no es administrador."},
        409: {"description": "Ya hay una corrida activa (`pipeline_run_in_progress`)."},
        422: {"description": "Rango no válido: no son lunes, al revés, con la semana en curso o de más de 26 semanas (`invalid_week_range`)."},
        503: {"description": "Prefect no está configurado o no respondió (`orchestrator_unavailable`), o la base no respondió (`reporting_unavailable`)."},
    },
)
def create_pipeline_run(
    request: PipelineRunRequest | None = Body(None),
    engine=Depends(get_engine),
    admin: User = Depends(require_admin),
) -> PipelineRunRead:
    request = request or PipelineRunRequest()
    try:
        run = trigger.trigger_pipeline_run(
            engine, week_from=request.week_from, week_to=request.week_to, requested_by=UUID(admin.id)
        )
    except trigger.InvalidWeekRange as error:
        raise ApiError(422, "invalid_week_range", str(error), details=[{"field": "week_from", "message": str(error)}]) from error
    except repository.PipelineRunInProgress as error:
        raise ApiError(409, "pipeline_run_in_progress", "Ya hay una corrida del pipeline en curso. Espera a que termine.") from error
    except trigger.OrchestratorUnavailable as error:
        logger.error(f"No se pudo pedir la corrida a Prefect: {error}")
        raise ApiError(503, "orchestrator_unavailable", "El orquestador del pipeline no está disponible. Vuelve a intentarlo.") from error
    except DBAPIError as error:
        raise _unavailable(error, "el log de corridas") from error
    logger.info(f"Corrida manual {run['id']} en cola: semanas {run['week_from']} a {run['week_to']}.")
    return PipelineRunRead.model_validate(run)
