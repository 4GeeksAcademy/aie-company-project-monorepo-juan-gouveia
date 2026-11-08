"""Inicialización de TinyDB para el directorio de proveedores.

TinyDB es el almacenamiento provisional que pidió el CTO: un archivo JSON, sin servidor.
Cuando exista Postgres, se sustituyen este módulo y repository.py; los endpoints no cambian.

El archivo (`storage/brasaland-db.json`) lo comparte también el gestor de incidencias; su ruta y
su apertura están en `app/core/storage.py`. Aquí se conservan los nombres de siempre.
"""

from app.core.storage import (
    BRASALAND_DB_PATH_ENV as DB_PATH_ENV,
    DEFAULT_BRASALAND_DB_PATH as DEFAULT_DB_PATH,
    get_brasaland_db_path as get_db_path,
    open_db,
)

SUPPLIERS_TABLE = "suppliers"

__all__ = ["DB_PATH_ENV", "DEFAULT_DB_PATH", "SUPPLIERS_TABLE", "get_db_path", "open_db"]
