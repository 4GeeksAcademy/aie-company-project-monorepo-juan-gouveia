"""Tabla `password_resets` (AUTH-03)."""

import uuid
from datetime import datetime, timedelta, timezone

from app.domains.auth.models import PasswordReset
from app.domains.users.database import AuthStore


def new_reset(user_id: str = "u-1") -> PasswordReset:
    now = datetime.now(timezone.utc)
    return PasswordReset(id=str(uuid.uuid4()), user_id=user_id, created_at=now, expires_at=now + timedelta(minutes=30))


def test_inserts_from_two_processes_do_not_collide(tmp_path):
    """Dos AuthStore sobre el mismo archivo simulan la API y otro proceso (un script, por ejemplo).

    TinyDB guarda en memoria el siguiente ID de cada tabla: sin calcularlo desde el archivo, la
    segunda inserción de la API chocaría con la del otro proceso (ValueError, 500 en la API).
    """
    path = tmp_path / "auth.json"
    api, other = AuthStore.from_path(path), AuthStore.from_path(path)
    try:
        first = new_reset()
        api.password_resets.insert(first)
        second = new_reset()
        other.password_resets.insert(second)
        third = new_reset()
        api.password_resets.insert(third)
        assert all(api.password_resets.get(reset.id) for reset in (first, second, third))
    finally:
        api.close()
        other.close()


def test_mark_all_used_only_touches_pending_links_of_the_user(tmp_path):
    store = AuthStore.from_path(tmp_path / "auth.json")
    try:
        mine, other_user = new_reset("u-1"), new_reset("u-2")
        store.password_resets.insert(mine)
        store.password_resets.insert(other_user)
        now = datetime.now(timezone.utc)
        assert store.password_resets.mark_all_used("u-1", now) == 1
        assert store.password_resets.get(mine.id).used_at is not None
        assert store.password_resets.get(other_user.id).used_at is None
        assert store.password_resets.mark_all_used("u-1", now) == 0
    finally:
        store.close()
