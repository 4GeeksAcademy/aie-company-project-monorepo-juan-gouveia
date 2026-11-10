"""Pruebas de integración HTTP de la autenticación (AUTH-088, decisión T-5).

Recorren la API con `TestClient`: comprueban el contrato con el backoffice (rutas protegidas,
códigos de estado, formato `{"error": {...}}` y cabeceras), que una prueba unitaria no ve.

Todas las de esta carpeta llevan el marker `integration`:
- `uv run pytest` las ejecuta junto con el resto;
- `uv run pytest -m integration` ejecuta solo estas;
- `uv run pytest -m "not integration"` las excluye.

Los fixtures (`api`, `make_user`, `auth_headers`…) vienen de `tests/conftest.py`.
"""

from pathlib import Path

import pytest

INTEGRATION_DIR = Path(__file__).parent


def pytest_collection_modifyitems(items):
    # El hook recibe todas las pruebas de la sesión: solo se marcan las de esta carpeta.
    for item in items:
        if INTEGRATION_DIR in item.path.parents:
            item.add_marker(pytest.mark.integration)
