"""Tokens de acceso y validación de la sesión: `core/security.py` y `get_current_user`.

La caducidad es la prioridad de AUTH-088: un refactor cambió la duración de los tokens sin que
ninguna prueba lo detectara.
"""

import base64
import json
from datetime import timedelta

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    ALGORITHM,
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    create_password_reset_token,
    decode_access_token,
    decode_access_token_claims,
)
from app.domains.auth.dependencies import BEARER_CHALLENGE, get_current_user
from app.domains.users import service as user_service
from app.domains.users.models import UserUpdate
from tests.auth.helpers import raises_api_error

LIFETIME = timedelta(minutes=30)  # ACCESS_TOKEN_EXPIRE_MINUTES del fixture auth_settings


def _raw_claims(token: str, key: str) -> dict:
    return jwt.decode(token, key, algorithms=[ALGORITHM], options={"verify_exp": False})


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


# --- Camino feliz ---------------------------------------------------------------------------


def test_tok_f1_token_carries_user_id_and_configured_lifetime(active_user, auth_settings, clock):
    claims = _raw_claims(create_access_token(active_user.id, now=clock.now), auth_settings.secret_key)

    assert claims["sub"] == active_user.id
    assert claims["iat"] == int(clock.now.timestamp())
    # En segundos: un cambio de unidades (segundos frente a minutos) rompe esta igualdad.
    assert claims["exp"] - claims["iat"] == 30 * 60


def test_tok_f2_valid_token_returns_user_from_store(active_user, auth_store, clock):
    token = create_access_token(active_user.id, now=clock.now)

    assert get_current_user(token=token, store=auth_store) == active_user


# --- Casos límite ---------------------------------------------------------------------------


def test_tok_l1_token_is_valid_one_second_before_expiry(active_user, clock):
    token = create_access_token(active_user.id, now=clock.ago(seconds=LIFETIME.total_seconds() - 1))

    assert decode_access_token(token) == active_user.id


def test_tok_l1_token_expires_one_second_after_lifetime(active_user, clock):
    token = create_access_token(active_user.id, now=clock.ago(seconds=LIFETIME.total_seconds() + 1))

    with pytest.raises(TokenExpiredError):
        decode_access_token(token)


def test_tok_l1_same_token_crosses_the_expiry_boundary(active_user, clock):
    """El mismo token, visto en dos instantes: justo antes y justo después de caducar."""
    token = create_access_token(active_user.id, now=clock.now)

    clock.advance(seconds=LIFETIME.total_seconds() - 1)
    assert decode_access_token(token) == active_user.id

    clock.advance(seconds=2)
    with pytest.raises(TokenExpiredError):
        decode_access_token(token)


@pytest.mark.parametrize("minutes", [1, 5, 120])
def test_tok_l2_lifetime_follows_setting(monkeypatch, minutes, active_user, clock):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(minutes))
    get_settings.cache_clear()  # auth_settings la vuelve a limpiar al terminar

    claims = _raw_claims(create_access_token(active_user.id, now=clock.now), get_settings().secret_key)

    assert claims["exp"] - claims["iat"] == minutes * 60


def test_tok_l3_token_from_same_second_as_password_change_is_valid(active_user, auth_store, clock):
    auth_store.users.update(active_user.id, {"password_changed_at": clock.now.isoformat()})
    token = create_access_token(active_user.id, now=clock.now)

    assert get_current_user(token=token, store=auth_store).id == active_user.id


def test_tok_l3_token_from_one_second_before_password_change_is_revoked(active_user, auth_store, clock):
    auth_store.users.update(active_user.id, {"password_changed_at": clock.now.isoformat()})
    token = create_access_token(active_user.id, now=clock.ago(seconds=1))

    with raises_api_error(401, "session_revoked"):
        get_current_user(token=token, store=auth_store)


# --- Modos de fallo -------------------------------------------------------------------------


def test_tok_x1_expired_token_is_token_expired_not_invalid(active_user, auth_store, clock):
    token = create_access_token(active_user.id, now=clock.ago(seconds=LIFETIME.total_seconds() + 1))

    with raises_api_error(401, "token_expired") as info:
        get_current_user(token=token, store=auth_store)
    assert info.value.headers == BEARER_CHALLENGE


def _secret() -> str:
    return get_settings().secret_key


def _bad_tokens(user_id: str, now) -> dict[str, str]:
    iat = int(now.timestamp())
    valid = {"iat": iat, "exp": iat + 600}
    return {
        "malformado": "esto-no-es-un-jwt",
        "otra firma": jwt.encode({"sub": user_id, **valid}, "otra-clave-que-no-es-la-de-la-api-0123", ALGORITHM),
        "sin sub": jwt.encode(valid, _secret(), ALGORITHM),
        "sub vacío": jwt.encode({"sub": "", **valid}, _secret(), ALGORITHM),
        "sub no texto": jwt.encode({"sub": 123, **valid}, _secret(), ALGORITHM),
        "sin iat": jwt.encode({"sub": user_id, "exp": iat + 600}, _secret(), ALGORITHM),
        "firma alterada": create_access_token(user_id, now=now)[:-4] + "AAAA",
    }


BAD_TOKEN_KINDS = ["malformado", "otra firma", "sin sub", "sub vacío", "sub no texto", "sin iat", "firma alterada"]


@pytest.mark.parametrize("kind", BAD_TOKEN_KINDS)
def test_tok_x2_bad_token_is_invalid_token(kind, active_user, auth_store, clock):
    token = _bad_tokens(active_user.id, clock.now)[kind]

    with pytest.raises(InvalidTokenError) as decoded:
        decode_access_token_claims(token)
    assert not isinstance(decoded.value, TokenExpiredError)

    with raises_api_error(401, "invalid_token") as info:
        get_current_user(token=token, store=auth_store)
    assert info.value.headers == BEARER_CHALLENGE


def test_tok_x2_empty_token_is_rejected_by_decoder():
    """Vacío en la lógica de tokens; en `get_current_user`, un token vacío es "sin token" (TOK-X5)."""
    with pytest.raises(InvalidTokenError):
        decode_access_token("")


def test_tok_x3_unsigned_alg_none_token_is_rejected(active_user, auth_store, clock):
    iat = int(clock.now.timestamp())
    token = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64({'sub': active_user.id, 'iat': iat, 'exp': iat + 600})}."

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
    with raises_api_error(401, "invalid_token"):
        get_current_user(token=token, store=auth_store)


def test_tok_x4_password_reset_token_is_not_a_session(active_user, auth_store, clock):
    token = create_password_reset_token(active_user.id, "jti-1", expires_at=clock.now + timedelta(minutes=30), now=clock.now)

    with raises_api_error(401, "invalid_token"):
        get_current_user(token=token, store=auth_store)


@pytest.mark.parametrize("token", [None, ""])
def test_tok_x5_missing_token_is_not_authenticated(token, auth_store):
    with raises_api_error(401, "not_authenticated") as info:
        get_current_user(token=token, store=auth_store)
    assert info.value.headers == BEARER_CHALLENGE


def test_tok_x6_token_of_deleted_user_is_invalid(active_user, auth_store, clock):
    token = create_access_token(active_user.id, now=clock.now)
    user_service.delete_user(auth_store, active_user.id)

    with raises_api_error(401, "invalid_token"):
        get_current_user(token=token, store=auth_store)


def test_tok_x6_token_of_deactivated_account_is_forbidden(active_user, auth_store, clock):
    token = create_access_token(active_user.id, now=clock.now)
    user_service.update_user(auth_store, active_user.id, UserUpdate(is_active=False))

    with raises_api_error(403, "inactive_user"):
        get_current_user(token=token, store=auth_store)


def test_tok_x6_token_issued_before_password_change_is_revoked(active_user, auth_store, clock):
    token = create_access_token(active_user.id, now=clock.now)
    auth_store.users.update(active_user.id, {"password_changed_at": clock.advance(minutes=1).isoformat()})

    with raises_api_error(401, "session_revoked"):
        get_current_user(token=token, store=auth_store)
