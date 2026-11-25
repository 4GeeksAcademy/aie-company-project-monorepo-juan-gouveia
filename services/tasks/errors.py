"""Qué fallos se reintentan (decisión T6 del plan).

**Transitorios** (se reintentan tras 10, 20 y 40 s): la base no responde, corta la conexión o cancela la
consulta por `statement_timeout`; el límite suave de la tarea (60 s); y el fallo transitorio inyectado
(T12). Con la base caída, el mismo informe puede salir bien unos segundos después.

**Permanentes** (fallan a la primera y van a la DLQ como `non_retryable`): falta la tabla, un error de
datos o de SQL, argumentos inválidos, falta `TASKS_DATABASE_URL`, el fallo permanente inyectado y cualquier
error de programación. Repetirlos solo retrasaría el mismo error.
"""

from __future__ import annotations

from celery.exceptions import SoftTimeLimitExceeded
from pandas.errors import DatabaseError as PandasDatabaseError
from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    InterfaceError,
    OperationalError,
)
from sqlalchemy.exc import TimeoutError as PoolTimeoutError


class InjectedTransientFault(RuntimeError):
    """Fallo transitorio forzado con TASKS_FAULT_INJECTION (solo para la demo de reintentos)."""


class InjectedPermanentFault(RuntimeError):
    """Fallo permanente forzado con TASKS_FAULT_INJECTION (solo para la demo de la DLQ)."""


TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (
    # OperationalError incluye la conexión rechazada o cortada y QueryCanceled (statement_timeout).
    OperationalError,
    InterfaceError,
    DisconnectionError,
    # El pool sin conexiones libres a tiempo.
    PoolTimeoutError,
    SoftTimeLimitExceeded,
    InjectedTransientFault,
)


def _unwrap(error: BaseException) -> BaseException:
    """pandas envuelve a veces el error de SQLAlchemy en su propio DatabaseError; el real es la causa."""
    if isinstance(error, PandasDatabaseError) and error.__cause__ is not None:
        return error.__cause__
    return error


def is_transient(error: BaseException) -> bool:
    error = _unwrap(error)
    if isinstance(error, TRANSIENT_ERRORS):
        return True
    # Un error del driver con la conexión invalidada (p. ej. el servidor la cerró a mitad de consulta).
    return isinstance(error, DBAPIError) and bool(error.connection_invalidated)


def describe(error: BaseException) -> str:
    """El error completo para el log y la DLQ: tipo y mensaje, con el del driver si lo hay."""
    error = _unwrap(error)
    message = str(error).strip()
    return f"{type(error).__name__}: {message}" if message else type(error).__name__
