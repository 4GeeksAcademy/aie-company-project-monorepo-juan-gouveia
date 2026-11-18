"""Protección de las rutas existentes (AUTH-01): incidentes y proveedores exigen un token válido.

Cubre los criterios del briefing:
- al menos 5 rutas fuera de /users y /auth requieren token (aquí, las 8 de incidents y suppliers);
- sin token, con token mal formado o caducado → 401;
- con un token válido siguen funcionando (sin regresiones).
"""

from datetime import timedelta

import pytest
from jose import jwt

from app.core.security import ALGORITHM, create_access_token

SUPPLIER = {
    "name": "Proveedor de Prueba",
    "country": "USA",
    "categories": ["lacteos"],
    "rate_per_unit": 3.2,
    "currency": "USD",
    "status": "active",
}
CSV = {"file": ("incidentes.csv", b"incident_id\n1\n", "text/csv")}

# (método, ruta, argumentos de la petición, códigos esperados con un token válido)
PROTECTED_ROUTES = [
    ("post", "/api/v1/incidents/analyze", {"files": CSV}, {422}),
    ("get", "/api/v1/incidents/results/export", {}, {404}),
    ("post", "/api/v1/suppliers", {"json": SUPPLIER}, {201}),
    ("get", "/api/v1/suppliers", {}, {200}),
    ("get", "/api/v1/suppliers/1", {}, {200}),
    ("patch", "/api/v1/suppliers/1/rate", {"json": {"rate_per_unit": 28600}}, {200}),
    ("patch", "/api/v1/suppliers/1/status", {"json": {"status": "suspended"}}, {200}),
    ("delete", "/api/v1/suppliers/2", {}, {200}),
]
IDS = [f"{method.upper()} {path}" for method, path, _, _ in PROTECTED_ROUTES]

# Rutas que deben seguir respondiendo sin token.
PUBLIC_ROUTES = {
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/users"),
    # AUTH-03: quien olvidó la contraseña no tiene sesión.
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/reset-password"),
    ("POST", "/api/v1/auth/reset-password/validate"),
    ("GET", "/health"),
}


def call(api, method, path, kwargs, headers=None):
    return getattr(api, method)(path, headers=headers or {}, **kwargs)


@pytest.mark.parametrize(("method", "path", "kwargs", "_ok"), PROTECTED_ROUTES, ids=IDS)
def test_without_token_is_401(api, method, path, kwargs, _ok):
    response = call(api, method, path, kwargs)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "not_authenticated"


@pytest.mark.parametrize(("method", "path", "kwargs", "_ok"), PROTECTED_ROUTES, ids=IDS)
@pytest.mark.parametrize("token", ["basura", "a.b.c", "eyJhbGciOiJub25lIn0.eyJzdWIiOiJ4In0."])
def test_with_malformed_token_is_401(api, method, path, kwargs, _ok, token):
    response = call(api, method, path, kwargs, {"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


@pytest.mark.parametrize(("method", "path", "kwargs", "_ok"), PROTECTED_ROUTES, ids=IDS)
def test_with_expired_token_is_401(api, make_user, method, path, kwargs, _ok):
    user, _ = make_user()
    token = create_access_token(user.id, expires_delta=timedelta(seconds=-1))
    response = call(api, method, path, kwargs, {"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


@pytest.mark.parametrize(("method", "path", "kwargs", "_ok"), PROTECTED_ROUTES, ids=IDS)
def test_with_token_signed_by_another_key_is_401(api, make_user, method, path, kwargs, _ok):
    user, _ = make_user()
    token = jwt.encode({"sub": user.id, "iat": 0, "exp": 4_000_000_000}, "otra-clave-0123456789-0123456789", ALGORITHM)
    response = call(api, method, path, kwargs, {"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "kwargs", "ok"), PROTECTED_ROUTES, ids=IDS)
def test_with_valid_token_works_as_before(api, auth_headers, method, path, kwargs, ok):
    # El arranque siembra los 15 proveedores del briefing; aún no hay análisis de incidentes (404),
    # y el CSV de prueba solo tiene una columna (422 missing_columns): son las respuestas de siempre.
    response = call(api, method, path, kwargs, auth_headers)
    assert response.status_code in ok, response.json()


def test_health_stays_public(api):
    assert api.get("/health").json() == {"status": "ok"}


def test_every_api_route_is_protected_unless_explicitly_public(api):
    """Evita que una ruta nueva quede abierta por olvido: o exige token o está en PUBLIC_ROUTES.

    Una ruta que depende de get_current_user declara en OpenAPI el esquema OAuth2PasswordBearer.
    """
    paths = api.get("/openapi.json").json()["paths"]
    unprotected = {
        (method.upper(), path)
        for path, operations in paths.items()
        for method, operation in operations.items()
        if {"OAuth2PasswordBearer": []} not in operation.get("security", [])
    }
    assert unprotected == PUBLIC_ROUTES


def test_at_least_five_protected_routes_outside_users_and_auth():
    protected = {(method, path) for method, path, _, _ in PROTECTED_ROUTES}
    assert len(protected) >= 5
    assert not any(path.startswith(("/api/v1/users", "/api/v1/auth")) for _, path in protected)
