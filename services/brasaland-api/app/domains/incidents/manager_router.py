"""Endpoints del gestor de incidencias centralizado. Solo traducen HTTP; los datos los guarda
incident_repository.py y el ciclo de vida está en models.py (TRANSITIONS).

- Los errores de validación responden 400 con el campo problemático (`BadRequestValidationRoute`).
- Las lecturas no fallan con la base vacía: lista vacía y métricas en 0.
- Los endpoints son síncronos porque TinyDB lo es; FastAPI los ejecuta en su pool de hilos.
"""

from fastapi import APIRouter, Depends, Query, status

from app.core.errors import ApiError, BadRequestValidationRoute
from app.domains.incidents.dependencies import get_incident_repository
from app.domains.incidents.exceptions import InvalidTransitionError
from app.domains.incidents.incident_repository import IncidentRepository
from app.domains.incidents.models import (
    Branch,
    Incident,
    IncidentCategory,
    IncidentCreate,
    IncidentOrigin,
    IncidentStatus,
    IncidentSummary,
    StatusUpdate,
)

router = APIRouter(prefix="/incidents", tags=["incident-manager"], route_class=BadRequestValidationRoute)

INVALID_REQUEST = {400: {"description": "Entrada inválida (`invalid_request`, con `details` por campo)"}}
NOT_FOUND = {404: {"description": "No existe ninguna incidencia con ese ID (`incident_not_found`)"}}


def found(incident: Incident | None, incident_id: int) -> Incident:
    if incident is None:
        raise ApiError(404, "incident_not_found", f"No existe ninguna incidencia con el ID {incident_id}.")
    return incident


def transition_error(error: InvalidTransitionError) -> ApiError:
    if not error.allowed:
        message = f"La incidencia está en {error.current.value}, un estado final: ya no puede cambiar."
    else:
        options = " o ".join(state.value for state in error.allowed)
        message = f"Desde {error.current.value} solo se puede pasar a {options}."
    return ApiError(400, "invalid_transition", message)


@router.post("", response_model=Incident, status_code=status.HTTP_201_CREATED, responses=INVALID_REQUEST)
def create_incident(
    data: IncidentCreate, repository: IncidentRepository = Depends(get_incident_repository)
) -> Incident:
    """Registra una incidencia nueva. Empieza siempre en `open`; `id`, `created_at` y `updated_at` los genera el sistema."""
    return repository.create(data)


@router.get("", response_model=list[Incident], responses=INVALID_REQUEST)
def list_incidents(
    status: IncidentStatus | None = Query(None, description="Filtra por estado"),
    origin: IncidentOrigin | None = Query(None, description="Filtra por origen"),
    branch: Branch | None = Query(None, description="Filtra por sede"),
    category: IncidentCategory | None = Query(None, description="Filtra por categoría"),
    repository: IncidentRepository = Depends(get_incident_repository),
) -> list[Incident]:
    """Lista las incidencias, de la más reciente a la más antigua. Los filtros se pueden combinar."""
    return repository.list(status=status, origin=origin, branch=branch, category=category)


# Antes de /{incident_id}, para que "summary" no se interprete como un ID.
@router.get("/summary", response_model=IncidentSummary)
def incident_summary(repository: IncidentRepository = Depends(get_incident_repository)) -> IncidentSummary:
    """Totales por estado, categoría, origen y sede. Incluye todos los valores, también los que están en 0."""
    return repository.summary()


@router.get("/{incident_id}", response_model=Incident, responses={**INVALID_REQUEST, **NOT_FOUND})
def get_incident(incident_id: int, repository: IncidentRepository = Depends(get_incident_repository)) -> Incident:
    """Detalle de una incidencia."""
    return found(repository.get(incident_id), incident_id)


@router.patch(
    "/{incident_id}/status",
    response_model=Incident,
    responses={
        400: {
            "description": "Entrada inválida (`invalid_request`) o transición no permitida por el ciclo de vida "
            "(`invalid_transition`)"
        },
        **NOT_FOUND,
    },
)
def update_incident_status(
    incident_id: int, data: StatusUpdate, repository: IncidentRepository = Depends(get_incident_repository)
) -> Incident:
    """Cambia solo el estado. open → in_progress | discarded; in_progress → resolved | discarded; resolved y discarded son finales."""
    try:
        incident = repository.update_status(incident_id, data.status)
    except InvalidTransitionError as error:
        raise transition_error(error) from None
    return found(incident, incident_id)
