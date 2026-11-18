"""Utilidades comunes de TinyDB.

`storage/brasaland-db.json` lo comparten varios dominios (proveedores e incidencias), cada uno con
su tabla y su instancia de TinyDB. TinyDB reescribe el archivo entero en cada escritura, así que dos
escrituras simultáneas desde hilos distintos podrían pisarse: por eso todos los repositorios de un
mismo archivo usan el mismo bloqueo (`lock_for`).
"""

import os
from pathlib import Path
from threading import Lock, RLock

from tinydb import TinyDB
from tinydb.table import Document, Table

SERVICE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BRASALAND_DB_PATH = SERVICE_ROOT / "storage" / "brasaland-db.json"
BRASALAND_DB_PATH_ENV = "BRASALAND_DB_PATH"

_locks: dict[Path, RLock] = {}
_locks_guard = Lock()


def get_brasaland_db_path() -> Path:
    """Ruta del archivo de datos de negocio: BRASALAND_DB_PATH si está definida; si no, storage/brasaland-db.json."""
    configured = os.environ.get(BRASALAND_DB_PATH_ENV)
    return Path(configured).expanduser().resolve() if configured else DEFAULT_BRASALAND_DB_PATH


def open_db(path: Path) -> TinyDB:
    """Abre (o crea) el archivo JSON en UTF-8, legible y con los acentos tal cual."""
    return TinyDB(path, create_dirs=True, encoding="utf-8", indent=2, ensure_ascii=False)


def lock_for(path: Path) -> RLock:
    """Bloqueo único por archivo dentro del proceso, compartido por todos los repositorios que lo usan.

    Es reentrante para que una operación de varios pasos pueda llamar a otras que también lo toman.
    No protege frente a otros procesos (por ejemplo, un script de seed con la API arrancada): para eso
    `insert_with_file_id` evita al menos la colisión de IDs.
    """
    key = Path(path).expanduser().resolve()
    with _locks_guard:
        return _locks.setdefault(key, RLock())


def insert_with_file_id(table: Table, record: dict) -> int:
    """Inserta `record` con un doc_id calculado a partir de lo que hay en el archivo.

    TinyDB recuerda en memoria el siguiente doc_id de cada tabla. Si otro proceso insertó después
    (por ejemplo, `uv run create-admin` con la API arrancada), la siguiente inserción de la API
    reutilizaría un ID ocupado y fallaría con ValueError (500). Leer el archivo lo evita, igual que
    hace suppliers/repository.py. Quien llama debe tener tomado el bloqueo de la tabla.
    """
    next_id = max((document.doc_id for document in table.all()), default=0) + 1
    table.insert(Document(record, doc_id=next_id))
    return next_id
