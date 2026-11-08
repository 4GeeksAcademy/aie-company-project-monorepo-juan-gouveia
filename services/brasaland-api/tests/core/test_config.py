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


# --- Restablecimiento de contraseña y correo (AUTH-03) --------------------------------------

BASE = {"SECRET_KEY": VALID_KEY, "ACCESS_TOKEN_EXPIRE_MINUTES": "15"}


def test_reset_and_email_defaults():
    settings = load_settings(BASE)
    assert settings.password_reset_expire_minutes == 30
    assert settings.resend_api_key is None and not settings.email_enabled
    assert settings.email_from == "Brasaland <onboarding@resend.dev>"
    assert settings.frontend_url == "http://localhost:3001"


@pytest.mark.parametrize("minutes", ["15", "45", "60"])
def test_reset_window_accepts_15_to_60_minutes(minutes):
    assert load_settings({**BASE, "PASSWORD_RESET_EXPIRE_MINUTES": minutes}).password_reset_expire_minutes == int(minutes)


@pytest.mark.parametrize("minutes", ["14", "61", "0", "media hora"])
def test_reset_window_outside_range_raises_error_naming_the_variable(minutes):
    with pytest.raises(ConfigError, match="PASSWORD_RESET_EXPIRE_MINUTES"):
        load_settings({**BASE, "PASSWORD_RESET_EXPIRE_MINUTES": minutes})


def test_resend_key_enables_email_and_is_not_shown_in_repr():
    settings = load_settings({**BASE, "RESEND_API_KEY": "re_clave_de_prueba"})
    assert settings.email_enabled
    assert "re_clave_de_prueba" not in repr(settings)


def test_custom_sender_and_frontend_url():
    settings = load_settings({**BASE, "EMAIL_FROM": "Brasaland <hola@brasaland.com>", "FRONTEND_URL": "https://bo.brasaland.com/"})
    assert settings.email_from == "Brasaland <hola@brasaland.com>"
    assert settings.frontend_url == "https://bo.brasaland.com"


def test_frontend_url_must_be_http():
    with pytest.raises(ConfigError, match="FRONTEND_URL"):
        load_settings({**BASE, "FRONTEND_URL": "backoffice.brasaland.com"})
