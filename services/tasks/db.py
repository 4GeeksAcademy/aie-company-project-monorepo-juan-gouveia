"""Conexión del worker a la base: el rol `task_worker` de la migración 007, leído de `TASKS_DATABASE_URL`.

Un motor por proceso, creado la primera vez que una tarea lo pide (no al importar: la API importa la
configuración de Celery y nunca abre esta conexión). `pool_pre_ping` descarta las conexiones que Supabase
cerró mientras el worker esperaba, en vez de fallar la primera tarea tras un rato sin trabajo.
"""

from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

DATABASE_URL_ENV = "TASKS_DATABASE_URL"
# Una tarea a la vez por proceso del pool (prefetch 1), más margen para record_dead_letter.
POOL_SIZE = 2


class MissingDatabaseUrl(RuntimeError):
    """Falta la variable de entorno TASKS_DATABASE_URL."""


def database_url() -> str:
    url = os.environ.get(DATABASE_URL_ENV, "").strip()
    if not url:
        raise MissingDatabaseUrl(
            "Falta TASKS_DATABASE_URL: la cadena del rol task_worker de la migración 007 "
            "(Supabase → Connect → Session pooler, usuario task_worker.<ref>)."
        )
    return url


def with_psycopg2_driver(url: str) -> str:
    """La cadena tal como la copia Supabase (`postgresql://...`), con el driver psycopg2 explícito.

    SQLAlchemy 2.1 usa por defecto psycopg (v3) para `postgresql://`, que no está instalado. Lo mismo
    hacen la API (`app.core.database`) y el script nocturno (`brasaland_jobs.job_runner`).
    """
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            return "postgresql+psycopg2://" + url.removeprefix(scheme)
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """El motor del proceso. Las pruebas lo sustituyen con `monkeypatch`."""
    return create_engine(
        with_psycopg2_driver(database_url()), pool_pre_ping=True, pool_size=POOL_SIZE, max_overflow=0
    )
