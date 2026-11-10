"""Utilidades comunes de las baterías unitarias (`tests/auth/`, `tests/suppliers/` y `tests/incidents/`)."""

from contextlib import contextmanager

import pytest

from app.core.errors import ApiError


@contextmanager
def raises_api_error(status_code: int, code: str):
    """Como `pytest.raises(ApiError)`, comprobando además el estado HTTP y el código de error."""
    with pytest.raises(ApiError) as info:
        yield info
    assert (info.value.status_code, info.value.code) == (status_code, code)
