"""Almacenamiento TinyDB de usuarios y perfiles.

Por directiva del briefing, `User` y `Profile` viven solo en TinyDB, también cuando llegue
PostgreSQL: las tablas de otros módulos guardarán solo el `id` del usuario como `user_uuid`.
Usan su propio archivo (no el de proveedores) y una sola instancia con un único bloqueo, porque
TinyDB reescribe el archivo entero en cada escritura.
"""

import os
from pathlib import Path
from threading import RLock

from tinydb import TinyDB

from app.domains.profiles.repository import ProfileRepository
from app.domains.users.repository import UserRepository

SERVICE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUTH_DB_PATH = SERVICE_ROOT / "storage" / "auth-db.json"
AUTH_DB_PATH_ENV = "AUTH_DB_PATH"


def get_auth_db_path() -> Path:
    """AUTH_DB_PATH si está definida; si no, storage/auth-db.json."""
    configured = os.environ.get(AUTH_DB_PATH_ENV)
    return Path(configured).expanduser().resolve() if configured else DEFAULT_AUTH_DB_PATH


def open_auth_db(path: Path) -> TinyDB:
    return TinyDB(path, create_dirs=True, encoding="utf-8", indent=2, ensure_ascii=False)


class AuthStore:
    """Un archivo, un bloqueo y los dos repositorios que lo comparten."""

    def __init__(self, db: TinyDB):
        self._db = db
        # Reentrante: los servicios lo toman en operaciones de varios pasos (usuario y perfil)
        # y los repositorios vuelven a tomarlo dentro.
        self.lock = RLock()
        self.users = UserRepository(db, self.lock)
        self.profiles = ProfileRepository(db, self.lock)

    @classmethod
    def from_path(cls, path: Path) -> "AuthStore":
        return cls(open_auth_db(path))

    def close(self) -> None:
        self._db.close()
