"""Conexión SQL del inventario (`app/core/database.py`): DATABASE_URL, sesión por petición y arranque."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, text

from app.core.config import ConfigError
from app.core.database import get_db, get_engine, load_database_url
from app.main import app

SUPABASE_URL = "postgresql://postgres.ref:secreto@aws-0-us-east-1.pooler.supabase.com:5432/postgres"


def test_reads_database_url_without_surrounding_spaces():
    assert load_database_url({"DATABASE_URL": f"  {SUPABASE_URL}  "}) == SUPABASE_URL


@pytest.mark.parametrize("environ", [{}, {"DATABASE_URL": "   "}])
def test_missing_database_url_raises_error_naming_the_variable(environ):
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        load_database_url(environ)


def test_postgres_scheme_is_rejected_with_a_hint():
    with pytest.raises(ConfigError, match="postgresql://"):
        load_database_url({"DATABASE_URL": SUPABASE_URL.replace("postgresql://", "postgres://")})


def test_get_db_yields_a_new_session_per_call_and_closes_it(inventory_engine):
    first_dependency = get_db(inventory_engine)
    first = next(first_dependency)
    second = next(get_db(inventory_engine))

    assert isinstance(first, Session)
    assert first is not second
    assert first.exec(text("SELECT 1")).one() == (1,)

    first_dependency.close()  # FastAPI cierra el generador al terminar la petición.
    assert not first.in_transaction()


def test_api_does_not_start_without_database_url(monkeypatch):
    # Sin el motor de pruebas, el arranque usa get_engine, que lee DATABASE_URL del entorno.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delitem(app.dependency_overrides, get_engine)
    get_engine.cache_clear()
    try:
        with pytest.raises(ConfigError, match="DATABASE_URL"):
            with TestClient(app):
                pass
    finally:
        get_engine.cache_clear()


def test_api_starts_with_both_connections(api, inventory_engine, auth_store):
    # TinyDB (auth) y el motor SQL (inventario) conviven en el mismo arranque.
    assert api.get("/health").json() == {"status": "ok"}
    assert app.dependency_overrides[get_engine]() is inventory_engine
