"""Lectura del catálogo de locales.

**Cache.** El catálogo solo cambia al ejecutar la migración 004, y cada consulta es una ida y vuelta a
Supabase. Se guarda el JSON ya serializado durante 10 minutos, como las lecturas del inventario: es igual
para cualquier usuario autenticado, así que la clave no lleva el usuario. Si se cambia una sede en la
base, el cambio tarda como mucho ese tiempo en verse (o un reinicio de la API).

Si la tabla no existe (falta la migración) o la base falla, se lanza `LocationsUnavailable`, que
`unavailable_response` convierte en el 503 `locations_unavailable` (lo usan el router y el inventario), sin
guardar nada en la cache.
"""

from pydantic import TypeAdapter
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.cache import TTLCache
from app.core.errors import ApiError
from app.core.logs import console_logger
from app.domains.locations.models import TABLE_NAME, Location
from app.domains.locations.schemas import LocationRead

logger = console_logger("api.locations")

CACHE_TTL_SECONDS = 600
CACHE_KEY = "locations"

locations_cache: TTLCache[bytes] = TTLCache(CACHE_TTL_SECONDS)

LOCATION_LIST = TypeAdapter(list[LocationRead])


class LocationsUnavailable(Exception):
    """La base no pudo devolver los locales; `missing_table` si falta la migración 004."""

    def __init__(self, reason: str, missing_table: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.missing_table = missing_table


def unavailable_response(error: LocationsUnavailable) -> ApiError:
    """Registra el fallo (pidiendo la migración si falta la tabla) y devuelve el 503 para el cliente."""
    if error.missing_table:
        logger.error(
            "No se pudo leer el catálogo de locales: falta la tabla locations. "
            "Ejecuta services/brasaland-api/migrations/004_locations.sql en Supabase."
        )
    else:
        logger.error(f"No se pudo leer el catálogo de locales: {error.reason}")
    return ApiError(503, "locations_unavailable", "No se pudieron cargar los locales. Vuelve a intentarlo.")


def _unavailable(error: SQLAlchemyError) -> LocationsUnavailable:
    """Resume el error de la base sin el SQL: el tipo y la primera línea del error del driver."""
    driver_error = getattr(error, "orig", None) or error
    detail = str(driver_error).strip()
    first_line = detail.splitlines()[0] if detail else "sin detalle"
    lowered = detail.lower()
    missing_table = TABLE_NAME in lowered and ("does not exist" in lowered or "no such table" in lowered)
    return LocationsUnavailable(f"{type(driver_error).__name__}: {first_line}", missing_table)


def list_locations(session: Session) -> list[LocationRead]:
    """Los 14 locales, ordenados por `id`."""
    try:
        rows = session.exec(select(Location).order_by(Location.id)).all()
    except SQLAlchemyError as error:
        raise _unavailable(error) from error
    return [LocationRead.model_validate(row, from_attributes=True) for row in rows]


def get_location(session: Session, location_id: int) -> Location | None:
    """El local con ese `id`, o `None` si no está en el catálogo. Lo usa el inventario al registrar órdenes."""
    try:
        return session.get(Location, location_id)
    except SQLAlchemyError as error:
        raise _unavailable(error) from error


def list_locations_json(session: Session) -> tuple[bytes, bool]:
    """El catálogo como JSON, desde la cache si está; el booleano dice si fue un acierto."""
    return locations_cache.get_or_load(CACHE_KEY, lambda: LOCATION_LIST.dump_json(list_locations(session)))
