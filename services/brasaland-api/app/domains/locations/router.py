"""Endpoint del catálogo de locales, `GET /locations` (montado en `/api/v1`).

Exige token, como el inventario (se registra con `get_current_user` en `app/main.py`). Es de solo
lectura: los locales cambian solo con la migración 004. La respuesta sale de la cache del servicio
(`X-Cache`); el `response_model` documenta el contrato en OpenAPI.
"""

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.logs import console_logger
from app.domains.locations.schemas import LocationRead
from app.domains.locations.service import LocationsUnavailable, list_locations_json

router = APIRouter(prefix="/locations", tags=["locations"])

logger = console_logger("api.locations")


@router.get(
    "",
    response_model=list[LocationRead],
    summary="Catálogo de los 14 locales",
    description=(
        "Los 14 locales de Brasaland ordenados por `id` (el `location_id` de las órdenes y de la telemetría), "
        "con su sede, ciudad, país y moneda. Se guarda 10 minutos (`X-Cache: HIT` o `MISS`)."
    ),
    responses={
        200: {"headers": {"X-Cache": {"description": "`HIT` si salió de la cache; `MISS` si se consultó la base"}}},
        503: {"description": "La base de datos no pudo responder (`locations_unavailable`)."},
    },
)
def get_locations(session: Session = Depends(get_db)) -> Response:
    try:
        body, hit = list_locations_json(session)
    except LocationsUnavailable as error:
        if error.missing_table:
            logger.error(
                "No se pudo leer el catálogo de locales: falta la tabla locations. "
                "Ejecuta services/brasaland-api/migrations/004_locations.sql en Supabase."
            )
        else:
            logger.error(f"No se pudo leer el catálogo de locales: {error.reason}")
        raise ApiError(
            503, "locations_unavailable", "No se pudieron cargar los locales. Vuelve a intentarlo."
        ) from error
    return Response(content=body, media_type="application/json", headers={"X-Cache": "HIT" if hit else "MISS"})
