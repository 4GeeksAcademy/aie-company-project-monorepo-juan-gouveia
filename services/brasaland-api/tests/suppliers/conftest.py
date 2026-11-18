"""Fixtures de la batería unitaria del directorio de proveedores (API-042).

Las pruebas llaman a las funciones de `suppliers/router.py` con el repositorio TinyDB temporal que
crea `tests/conftest.py` (`supplier_repository`, vacío en cada prueba), sin HTTP.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.domains.suppliers import repository as repository_module
from app.domains.suppliers.models import Supplier, SupplierCreate
from tests.suppliers.helpers import supplier_data


@pytest.fixture
def repository(supplier_repository):
    """El repositorio temporal de proveedores, con un nombre corto."""
    return supplier_repository


@pytest.fixture
def add_supplier(repository):
    """Guarda un proveedor directamente en el repositorio y lo devuelve."""

    def add(**changes) -> Supplier:
        return repository.create(SupplierCreate(**supplier_data(**changes)))

    return add


class FrozenClock:
    """Reloj del repositorio de proveedores (`utc_now`), que solo avanza con `advance`."""

    def __init__(self):
        self.now = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> datetime:
        self.now += timedelta(**delta)
        return self.now


@pytest.fixture
def clock(monkeypatch) -> FrozenClock:
    """Fija la hora con la que el repositorio escribe `updated_at`."""
    frozen = FrozenClock()
    monkeypatch.setattr(repository_module, "utc_now", frozen)
    return frozen
