"""Piezas que los endpoints de usuarios, perfiles y autenticación reciben por inyección."""

from threading import Lock

from app.domains.users.database import AuthStore, get_auth_db_path

_store: AuthStore | None = None
_lock = Lock()


def get_auth_store() -> AuthStore:
    """Una sola instancia por proceso, creada al primer uso. Las pruebas la sustituyen."""
    global _store
    with _lock:
        if _store is None:
            _store = AuthStore.from_path(get_auth_db_path())
        return _store
