"""Piezas que los endpoints del dominio reciben por inyección de dependencias."""

from threading import Lock

from app.core.storage import get_brasaland_db_path
from app.domains.incidents.incident_repository import IncidentRepository
from app.domains.incidents.repository import LastAnalysisRepository

# Analizador del CSV: una sola instancia por proceso; el "último análisis" es compartido por todas las peticiones.
_repository = LastAnalysisRepository()

# Gestor de incidencias: se crea al primer uso, así importar la app no crea el archivo.
_incident_repository: IncidentRepository | None = None
_incident_lock = Lock()


def get_repository() -> LastAnalysisRepository:
    return _repository


def get_incident_repository() -> IncidentRepository:
    """Repositorio del gestor sobre storage/brasaland-db.json (o BRASALAND_DB_PATH)."""
    global _incident_repository
    with _incident_lock:
        if _incident_repository is None:
            _incident_repository = IncidentRepository.from_path(get_brasaland_db_path())
        return _incident_repository
