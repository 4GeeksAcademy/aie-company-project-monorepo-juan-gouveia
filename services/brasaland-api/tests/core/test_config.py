import pytest
from fastapi.testclient import TestClient

from app.core.config import ConfigError, get_settings, load_settings
from app.main import app

VALID_KEY = "k" * 32


def test_reads_secret_key_and_expiration():
    settings = load_settings({"SECRET_KEY": VALID_KEY, "ACCESS_TOKEN_EXPIRE_MINUTES": "15"})
    assert settings.secret_key == VALID_KEY
    assert settings.access_token_expire_minutes == 15


def test_secret_key_is_not_shown_in_repr():
    settings = load_settings({"SECRET_KEY": VALID_KEY, "ACCESS_TOKEN_EXPIRE_MINUTES": "15"})
    assert VALID_KEY not in repr(settings)


@pytest.mark.parametrize(
    ("environ", "variable"),
    [
        ({"ACCESS_TOKEN_EXPIRE_MINUTES": "15"}, "SECRET_KEY"),
        ({"SECRET_KEY": "   ", "ACCESS_TOKEN_EXPIRE_MINUTES": "15"}, "SECRET_KEY"),
        ({"SECRET_KEY": "corta", "ACCESS_TOKEN_EXPIRE_MINUTES": "15"}, "SECRET_KEY"),
        ({"SECRET_KEY": VALID_KEY}, "ACCESS_TOKEN_EXPIRE_MINUTES"),
        ({"SECRET_KEY": VALID_KEY, "ACCESS_TOKEN_EXPIRE_MINUTES": "treinta"}, "ACCESS_TOKEN_EXPIRE_MINUTES"),
        ({"SECRET_KEY": VALID_KEY, "ACCESS_TOKEN_EXPIRE_MINUTES": "0"}, "ACCESS_TOKEN_EXPIRE_MINUTES"),
        ({"SECRET_KEY": VALID_KEY, "ACCESS_TOKEN_EXPIRE_MINUTES": "-5"}, "ACCESS_TOKEN_EXPIRE_MINUTES"),
    ],
)
def test_missing_or_invalid_values_raise_error_naming_the_variable(environ, variable):
    with pytest.raises(ConfigError, match=variable):
        load_settings(environ)


def test_reads_from_process_environment(auth_settings):
    # El fixture autouse define las variables de prueba en el entorno.
    assert get_settings().access_token_expire_minutes == 30


def test_api_does_not_start_without_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")
    get_settings.cache_clear()
    with pytest.raises(ConfigError, match="SECRET_KEY"):
        with TestClient(app):
            pass
