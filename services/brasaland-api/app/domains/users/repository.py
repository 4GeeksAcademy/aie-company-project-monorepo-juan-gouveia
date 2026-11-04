"""Acceso a los usuarios guardados en TinyDB. Solo esta pieza y la de perfiles conocen TinyDB."""

# `list` es un método de la clase; las anotaciones se evalúan en diferido.
from __future__ import annotations

from threading import RLock

from tinydb import Query, TinyDB

from app.domains.users.models import User

USERS_TABLE = "users"


class UserRepository:
    def __init__(self, db: TinyDB, lock: RLock):
        # Sin caché de consultas: así se ven los cambios de `uv run create-admin` desde otro proceso.
        self._table = db.table(USERS_TABLE, cache_size=0)
        self._lock = lock

    def list(self) -> list[User]:
        """Todos los usuarios, por fecha de alta."""
        with self._lock:
            documents = self._table.all()
        return sorted((User(**document) for document in documents), key=lambda user: user.created_at)

    def get(self, user_id: str) -> User | None:
        with self._lock:
            document = self._table.get(Query().id == user_id)
        return None if document is None else User(**document)

    def get_by_email(self, email: str) -> User | None:
        """Busca por email ya normalizado (minúsculas, sin espacios extremos)."""
        with self._lock:
            document = self._table.get(Query().email == email)
        return None if document is None else User(**document)

    def insert(self, user: User) -> None:
        with self._lock:
            self._table.insert(user.model_dump(mode="json"))

    def update(self, user_id: str, changes: dict) -> User | None:
        """Aplica cambios ya validados y serializados. None si el usuario no existe."""
        with self._lock:
            if not self._table.update(changes, Query().id == user_id):
                return None
            document = self._table.get(Query().id == user_id)
        return User(**document)

    def delete(self, user_id: str) -> User | None:
        """Elimina y devuelve el usuario; None si no existe."""
        with self._lock:
            document = self._table.get(Query().id == user_id)
            if document is None:
                return None
            self._table.remove(Query().id == user_id)
        return User(**document)
