"""Piezas que los endpoints del dominio reciben por inyección de dependencias."""

from app.domains.incidents.repository import LastAnalysisRepository

# Una sola instancia por proceso: el "último análisis" es compartido por todas las peticiones.
_repository = LastAnalysisRepository()


def get_repository() -> LastAnalysisRepository:
    return _repository
