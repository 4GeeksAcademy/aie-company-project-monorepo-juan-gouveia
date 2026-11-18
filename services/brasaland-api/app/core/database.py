"""Conexión SQL de la API: motor SQLModel sobre Supabase (PostgreSQL) y sesión por petición.

La API mantiene dos conexiones de base de datos a la vez, cada una con su responsabilidad:

- **TinyDB** (sin cambios): usuarios, perfiles y autenticación en `storage/auth-db.json`
  (`app/domains/users/database.py`), y proveedores e incidencias en `storage/brasaland-db.json`
  (`app/core/storage.py`). Las consultas de usuario (`get_current_user`) van siempre ahí.
- **Supabase** (este módulo): las entidades de inventario del Hito 5 (`Ingredient`,
  `IngredientEntry` e `IngredientExit`). Ninguna tabla de usuarios se replica aquí: las órdenes solo
  guardan el `user_uuid` del usuario de TinyDB.

La cadena de conexión se lee de `DATABASE_URL` (en local, desde `.env`; ver `.env.example`). Nunca
se escribe en el código. Sin ella, la API no arranca.

`get_db` abre una `Session` nueva en cada petición y la cierra al terminar: no hay sesiones
globales. Las pruebas sustituyen `get_engine` por un motor SQLite temporal.
"""

import os
from collections.abc import Iterator
from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import ConfigError

if TYPE_CHECKING:
    # Solo para las anotaciones: SQLModel no reexporta el tipo del motor. En ejecución, la API no
    # importa SQLAlchemy; todo pasa por sqlmodel (consigna del Hito 5).
    from sqlalchemy import Engine

DATABASE_URL_ENV = "DATABASE_URL"
POSTGRESQL_SCHEME = "postgresql://"
# Driver que instala la consigna (psycopg2-binary). SQLAlchemy 2.1 usa por defecto psycopg (v3)
# para postgresql://, que no está instalado: sin indicarlo, la conexión falla con ModuleNotFoundError.
PSYCOPG2_SCHEME = "postgresql+psycopg2://"


def load_database_url(environ=os.environ) -> str:
    """Lee y valida DATABASE_URL; lanza ConfigError con un mensaje que nombra la variable.

    Acepta la cadena tal como la copia Supabase (postgresql://...) y la devuelve con el driver
    psycopg2 explícito.
    """
    url = environ.get(DATABASE_URL_ENV, "").strip()
    if not url:
        raise ConfigError(
            f"Falta la variable de entorno {DATABASE_URL_ENV} (cadena de conexión PostgreSQL de Supabase)."
        )
    if url.startswith("postgres://"):
        # SQLAlchemy solo reconoce el esquema postgresql://.
        raise ConfigError(f"{DATABASE_URL_ENV} debe empezar por postgresql://, no por postgres://.")
    if url.startswith(POSTGRESQL_SCHEME):
        url = PSYCOPG2_SCHEME + url.removeprefix(POSTGRESQL_SCHEME)
    return url


@lru_cache
def get_engine() -> "Engine":
    """Motor único del proceso, creado al primer uso (el pool de conexiones se comparte).

    pool_pre_ping comprueba la conexión antes de usarla: Supabase cierra las inactivas.
    """
    return create_engine(load_database_url(), pool_pre_ping=True)


def init_db(engine: "Engine") -> None:
    """Crea en la base las tablas de inventario que aún no existan (no modifica las que ya existen).

    Los modelos se registran en `SQLModel.metadata` al importar su módulo; importarlo aquí garantiza
    que estén todos, sea cual sea el orden de importación.
    """
    import app.domains.inventory.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_db(engine=Depends(get_engine)) -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión SQLModel por petición, cerrada siempre al terminar.

    `engine` va sin anotación: FastAPI evalúa las anotaciones de las dependencias en ejecución, y el
    tipo `Engine` solo se importa para el análisis estático.
    """
    with Session(engine) as session:
        yield session
