"""Piezas que los endpoints del dominio reciben por inyección de dependencias."""

from threading import Lock

from app.domains.suppliers.database import get_db_path
from app.domains.suppliers.repository import SupplierRepository

_repository: SupplierRepository | None = None
_lock = Lock()


def get_repository() -> SupplierRepository:
    """Una sola instancia por proceso. Se crea al primer uso, así importar la app no crea el archivo."""
    global _repository
    with _lock:
        if _repository is None:
            _repository = SupplierRepository.from_path(get_db_path())
        return _repository
