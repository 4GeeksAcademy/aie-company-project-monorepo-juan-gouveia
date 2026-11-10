"""Fixtures de la batería unitaria de autenticación (AUTH-088).

Las pruebas de esta carpeta llaman directamente a las funciones de cada endpoint y a sus servicios,
sin `TestClient` (decisión T-3). Comprueban la decisión (token emitido, `ApiError` con su código,
estado guardado), no el JSON de la respuesta.

De `tests/conftest.py` llegan, en todas las pruebas: `auth_settings` (`SECRET_KEY` de pruebas y
30 minutos de validez), `auth_store` (TinyDB temporal) y `email_sender` (correo falso).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pytest

from app.domains.users import service as user_service
from app.domains.users.models import Role, User, UserCreate, UserUpdate

PASSWORD = "parrilla-segura"


@pytest.fixture
def user_factory(auth_store):
    """Crea un usuario en la base temporal y lo devuelve. Por defecto: rol `user`, activo y PASSWORD.

    bcrypt es lento a propósito: cada usuario cuesta unos 0,2 s, así que conviene crear solo los
    que la prueba necesita.
    """

    def create(
        email: str = "ana@brasaland.com",
        *,
        role: Role = Role.USER,
        password: str = PASSWORD,
        is_active: bool = True,
        **profile,
    ) -> User:
        user, _ = user_service.create_user(
            auth_store, UserCreate(email=email, password=password, **profile), role=role
        )
        if not is_active:
            user = user_service.update_user(auth_store, user.id, UserUpdate(is_active=False))
        return user

    return create


@pytest.fixture
def active_user(user_factory) -> User:
    """Usuario normal (rol `user`) y activo, con la contraseña PASSWORD."""
    return user_factory("ana@brasaland.com")


@pytest.fixture
def inactive_user(user_factory) -> User:
    """Usuario normal desactivado por un admin, con la contraseña PASSWORD."""
    return user_factory("baja@brasaland.com", is_active=False)


@pytest.fixture
def admin_user(user_factory) -> User:
    """Administrador activo, con la contraseña PASSWORD."""
    return user_factory("admin@brasaland.com", role=Role.ADMIN)


@dataclass
class Clock:
    """Reloj controlado para las funciones que aceptan `now`.

    Empieza en el instante real, en segundos enteros (como `iat`), y solo avanza con `advance`.
    python-jose comprueba `exp` con el reloj real, así que un token emitido con `clock.now` es
    válido de verdad; para probar la caducidad se emite con un `now` anterior (`clock.ago(...)`).
    """

    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))

    def advance(self, **delta: float) -> datetime:
        """Avanza el reloj (`advance(minutes=31)`) y devuelve el nuevo instante."""
        self.now += timedelta(**delta)
        return self.now

    def ago(self, **delta: float) -> datetime:
        """Instante anterior al actual, sin mover el reloj (`ago(minutes=30, seconds=1)`)."""
        return self.now - timedelta(**delta)


@pytest.fixture
def clock() -> Clock:
    return Clock()
