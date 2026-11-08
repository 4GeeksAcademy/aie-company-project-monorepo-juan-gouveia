from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    ALGORITHM,
    InvalidTokenError,
    TokenExpiredError,
    PASSWORD_RESET_PURPOSE,
    create_access_token,
    create_password_reset_token,
    decode_access_token,
    decode_access_token_claims,
    decode_password_reset_token,
    hash_password,
    verify_password,
)

USER_ID = "3f1c2a4e-8b7d-4c6e-9a0b-1d2e3f4a5b6c"

# --- Contraseñas ---------------------------------------------------------------------------


def test_hash_is_bcrypt_and_does_not_contain_plain_text():
    hashed = hash_password("parrilla-segura")
    assert hashed.startswith("$2b$")
    assert "parrilla-segura" not in hashed


def test_same_password_gives_different_hashes():
    assert hash_password("parrilla-segura") != hash_password("parrilla-segura")


def test_verify_accepts_right_password_and_rejects_wrong_one():
    hashed = hash_password("parrilla-segura")
    assert verify_password("parrilla-segura", hashed) is True
    assert verify_password("parrilla-insegura", hashed) is False


def test_verify_without_hash_is_false():
    # Email inexistente: se compara contra un hash de referencia y siempre falla.
    assert verify_password("parrilla-segura", None) is False


def test_verify_handles_too_long_password_and_bad_hash():
    hashed = hash_password("parrilla-segura")
    assert verify_password("x" * 80, hashed) is False
    assert verify_password("parrilla-segura", "no-es-un-hash") is False


# --- Tokens --------------------------------------------------------------------------------


def test_token_round_trip_returns_user_id():
    assert decode_access_token(create_access_token(USER_ID)) == USER_ID


def test_token_contains_only_expected_claims_and_configured_expiration():
    now = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    token = create_access_token(USER_ID, now=now)
    claims = jwt.get_unverified_claims(token)
    assert set(claims) == {"sub", "iat", "exp"}
    assert claims["sub"] == USER_ID
    # ACCESS_TOKEN_EXPIRE_MINUTES = 30 en las pruebas.
    assert claims["exp"] - claims["iat"] == 30 * 60


def test_expiration_follows_environment_variable(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
    get_settings.cache_clear()
    claims = jwt.get_unverified_claims(create_access_token(USER_ID))
    assert claims["exp"] - claims["iat"] == 5 * 60


def test_expired_token_is_rejected():
    token = create_access_token(USER_ID, expires_delta=timedelta(seconds=-1))
    with pytest.raises(TokenExpiredError):
        decode_access_token(token)


def test_token_signed_with_another_key_is_rejected():
    claims = {"sub": USER_ID, "iat": 0, "exp": 4_000_000_000}
    token = jwt.encode(claims, "otra-clave-que-no-es-la-de-la-api-000000", algorithm=ALGORITHM)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    header, payload, signature = create_access_token(USER_ID).split(".")
    tampered = jwt.encode({"sub": "otro-usuario", "iat": 0, "exp": 4_000_000_000}, "x" * 32).split(".")[1]
    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{header}.{tampered}.{signature}")


def test_unsigned_token_is_rejected():
    # alg "none": un token sin firma nunca se acepta.
    unsigned = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ4IiwiaWF0IjowLCJleHAiOjQwMDAwMDAwMDB9."
    with pytest.raises(InvalidTokenError):
        decode_access_token(unsigned)


@pytest.mark.parametrize("token", ["", "basura", "a.b.c", "x.y.z", "ñ.ñ.ñ"])
def test_malformed_token_is_rejected(token):
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize(
    "claims",
    [
        {"iat": 0, "exp": 4_000_000_000},  # sin sub
        {"sub": USER_ID, "iat": 0},  # sin exp
        {"sub": USER_ID, "exp": 4_000_000_000},  # sin iat
        {"sub": "", "iat": 0, "exp": 4_000_000_000},  # sub vacío
    ],
)
def test_token_missing_claims_is_rejected(auth_settings, claims):
    token = jwt.encode(claims, auth_settings.secret_key, algorithm=ALGORITHM)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


# --- Tokens de restablecimiento (AUTH-03) ---------------------------------------------------


def reset_token(expires_in: timedelta = timedelta(minutes=30)) -> str:
    return create_password_reset_token(USER_ID, "jti-1", expires_at=datetime.now(timezone.utc) + expires_in)


def test_reset_token_round_trip():
    claims = decode_password_reset_token(reset_token())
    assert (claims.subject, claims.token_id) == (USER_ID, "jti-1")


def test_reset_token_carries_its_purpose():
    claims = jwt.get_unverified_claims(reset_token())
    assert claims["purpose"] == PASSWORD_RESET_PURPOSE
    assert {"sub", "jti", "iat", "exp"} <= set(claims)


def test_reset_token_is_not_accepted_as_an_access_token():
    with pytest.raises(InvalidTokenError):
        decode_access_token(reset_token())


def test_access_token_is_not_accepted_as_a_reset_token():
    with pytest.raises(InvalidTokenError):
        decode_password_reset_token(create_access_token(USER_ID))


def test_expired_reset_token_raises_expired():
    with pytest.raises(TokenExpiredError):
        decode_password_reset_token(reset_token(timedelta(seconds=-1)))


def test_reset_token_without_jti_is_rejected(auth_settings):
    claims = {"sub": USER_ID, "purpose": PASSWORD_RESET_PURPOSE, "iat": 0, "exp": 4_000_000_000}
    with pytest.raises(InvalidTokenError):
        decode_password_reset_token(jwt.encode(claims, auth_settings.secret_key, ALGORITHM))


def test_access_token_claims_include_issue_time():
    now = datetime(2026, 11, 6, 10, 0, 0, tzinfo=timezone.utc)
    token = create_access_token(USER_ID, now=now, expires_delta=timedelta(days=36500))
    claims = decode_access_token_claims(token)
    assert (claims.subject, claims.issued_at) == (USER_ID, int(now.timestamp()))
