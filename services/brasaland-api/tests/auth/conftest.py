"""Fixtures de la batería unitaria de autenticación (AUTH-088).

Las pruebas de esta carpeta llaman directamente a las funciones de cada endpoint y a sus servicios,
sin `TestClient` (decisión T-3). Comprueban la decisión (token emitido, `ApiError` con su código,
estado guardado), no el JSON de la respuesta.

De `tests/conftest.py` llegan, en todas las pruebas: `auth_settings` (`SECRET_KEY` de pruebas y
30 minutos de validez), `auth_store` (TinyDB temporal) y `email_sender` (correo falso).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import jose.jwt
import pytest

from app.domains.users import service as user_service
from app.domains.users.models import Role, User, UserCreate, UserUpdate
from tests.auth.helpers import PASSWORD


@pytest.fixture
def anyio_backend():
    """Las funciones de ruta async se ejecutan con `@pytest.mark.anyio` sobre asyncio (plugin de anyio)."""
    return "asyncio"


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
    El fixture `clock` hace además que python-jose compruebe `exp` con este reloj, así que las
    fronteras de caducidad se prueban al segundo exacto y sin esperas.
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
def clock(monkeypatch) -> Clock:
    """Reloj controlado, compartido con python-jose.

    jose calcula el instante actual con `datetime.now(UTC)` dentro de `jose.jwt`; se sustituye ese
    `datetime` por uno cuyo `now` devuelve `clock.now`. El resto de la API sigue con el reloj real:
    a las funciones de la lógica se les pasa `now=clock.now`.
    """
    current = Clock()

    class ClockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return current.now if tz is None else current.now.astimezone(tz)

    assert jose.jwt.datetime is datetime, "python-jose cambió cómo lee la hora: revisar el fixture clock"
    monkeypatch.setattr(jose.jwt, "datetime", ClockDatetime)
    return current
