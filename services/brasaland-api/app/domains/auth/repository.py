"""Acceso a la tabla `password_resets` de TinyDB (archivo de usuarios y perfiles)."""

from datetime import datetime
from threading import RLock

from tinydb import Query, TinyDB

from app.core.storage import insert_with_file_id
from app.domains.auth.models import PasswordReset

PASSWORD_RESETS_TABLE = "password_resets"


class PasswordResetRepository:
    def __init__(self, db: TinyDB, lock: RLock):
        # Sin caché de consultas, como los repositorios de usuarios y perfiles.
        self._table = db.table(PASSWORD_RESETS_TABLE, cache_size=0)
        self._lock = lock

    def insert(self, reset: PasswordReset) -> None:
        with self._lock:
            insert_with_file_id(self._table, reset.model_dump(mode="json"))

    def get(self, reset_id: str) -> PasswordReset | None:
        with self._lock:
            document = self._table.get(Query().id == reset_id)
        return None if document is None else PasswordReset(**document)

    def count_created_since(self, user_id: str, since: datetime) -> int:
        """Solicitudes del usuario desde `since` (para el límite por hora)."""
        with self._lock:
            documents = self._table.search(Query().user_id == user_id)
        return sum(1 for document in documents if PasswordReset(**document).created_at >= since)

    def mark_all_used(self, user_id: str, used_at: datetime) -> int:
        """Marca como usados todos los enlaces pendientes del usuario. Devuelve cuántos."""
        reset = Query()
        with self._lock:
            updated = self._table.update(
                {"used_at": used_at.isoformat()}, (reset.user_id == user_id) & (reset.used_at == None)  # noqa: E711
            )
        return len(updated)

    def delete_for_user(self, user_id: str) -> None:
        with self._lock:
            self._table.remove(Query().user_id == user_id)
