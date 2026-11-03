"""Inicialización de TinyDB para el directorio de proveedores.

TinyDB es el almacenamiento provisional que pidió el CTO: un archivo JSON, sin servidor.
Cuando exista Postgres, se sustituyen este módulo y repository.py; los endpoints no cambian.
"""

import os
from pathlib import Path

from tinydb import TinyDB

SERVICE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = SERVICE_ROOT / "storage" / "brasaland-db.json"
DB_PATH_ENV = "BRASALAND_DB_PATH"
SUPPLIERS_TABLE = "suppliers"


def get_db_path() -> Path:
    """Ruta del archivo de la base: BRASALAND_DB_PATH si está definida; si no, storage/brasaland-db.json."""
    configured = os.environ.get(DB_PATH_ENV)
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH


def open_db(path: Path) -> TinyDB:
    """Abre (o crea) el archivo JSON en UTF-8, legible y con los acentos tal cual."""
    return TinyDB(path, create_dirs=True, encoding="utf-8", indent=2, ensure_ascii=False)
