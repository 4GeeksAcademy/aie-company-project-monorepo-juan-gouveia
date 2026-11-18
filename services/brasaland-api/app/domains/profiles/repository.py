"""Acceso a los perfiles guardados en TinyDB.

Comparte archivo y bloqueo con los usuarios (los recibe al crearse), para que crear o borrar un
usuario junto con su perfil ocurra bajo el mismo bloqueo.
"""

import uuid
from threading import RLock

from tinydb import Query, TinyDB

from app.core.storage import insert_with_file_id
from app.domains.profiles.models import Profile, ProfileFields, ProfileUpdate

PROFILES_TABLE = "profiles"


class ProfileRepository:
    def __init__(self, db: TinyDB, lock: RLock):
        # Sin caché de consultas, igual que en suppliers: se ven los cambios de otros procesos.
        self._table = db.table(PROFILES_TABLE, cache_size=0)
        self._lock = lock

    def get_by_user_id(self, user_id: str) -> Profile | None:
        with self._lock:
            document = self._table.get(Query().user_id == user_id)
        return None if document is None else Profile(**document)

    def create_for_user(self, user_id: str, fields: ProfileFields | None = None) -> Profile:
        """Crea el perfil del usuario; los campos que no se envíen quedan en null."""
        values = (fields or ProfileFields()).model_dump(include={"name", "phone", "address"})
        profile = Profile(id=str(uuid.uuid4()), user_id=user_id, **values)
        with self._lock:
            # doc_id desde el archivo: `uv run create-admin` puede insertar desde otro proceso.
            insert_with_file_id(self._table, profile.model_dump(mode="json"))
        return profile

    def update_for_user(self, user_id: str, changes: ProfileUpdate) -> Profile | None:
        """Aplica solo los campos enviados. None si el usuario no tiene perfil."""
        with self._lock:
            updated = self._table.update(changes.model_dump(exclude_unset=True), Query().user_id == user_id)
            if not updated:
                return None
            document = self._table.get(Query().user_id == user_id)
        return Profile(**document)

    def delete_for_user(self, user_id: str) -> bool:
        with self._lock:
            return bool(self._table.remove(Query().user_id == user_id))
