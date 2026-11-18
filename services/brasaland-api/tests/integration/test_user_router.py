"""CRUD de /users: registro público, rutas protegidas y 403 entre usuarios."""

import pytest

from app.domains.users import service
from app.domains.users.models import Role

USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"


# --- POST /users (público) ---------------------------------------------------------------


def test_register_creates_user_with_role_user_and_profile(api, auth_store):
    payload = {"email": "Ana@Brasaland.com", "password": "parrilla-segura", "name": "Ana", "phone": "+57 300"}
    response = api.post(USERS, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@brasaland.com"
    assert body["role"] == "user" and body["is_active"] is True
    assert body["profile"]["user_id"] == body["id"]
    assert body["profile"]["name"] == "Ana" and body["profile"]["address"] is None
    assert "password" not in body and "hashed_password" not in body
    # El registro sirve para iniciar sesión.
    assert api.post(LOGIN, json={"email": "ana@brasaland.com", "password": "parrilla-segura"}).status_code == 200


def test_register_without_profile_data(api):
    response = api.post(USERS, json={"email": "ana@brasaland.com", "password": "parrilla-segura"})
    assert response.status_code == 201
    assert response.json()["profile"]["name"] is None


def test_register_rejects_role_so_nobody_self_promotes(api, auth_store):
    response = api.post(USERS, json={"email": "ana@brasaland.com", "password": "parrilla-segura", "role": "admin"})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "role"
    assert service.list_users(auth_store) == []


def test_register_duplicate_email_is_409(api, make_user):
    make_user()
    response = api.post(USERS, json={"email": "ANA@brasaland.com", "password": "parrilla-segura"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_email"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "ana", "password": "parrilla-segura"},
        {"email": "ana@brasaland.com", "password": "corta"},
        {"email": "ana@brasaland.com"},
        {"email": "ana@brasaland.com", "password": "parrilla-segura", "name": "   "},
    ],
)
def test_register_invalid_input_is_422(api, payload):
    assert api.post(USERS, json=payload).status_code == 422


# --- Rutas protegidas sin token -------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", USERS), ("get", f"{USERS}/x"), ("put", f"{USERS}/x"), ("delete", f"{USERS}/x")],
)
def test_protected_user_routes_without_token_are_401(api, method, path):
    kwargs = {"json": {"email": "a@b.co"}} if method == "put" else {}
    response = getattr(api, method)(path, **kwargs)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


# --- GET /users ---------------------------------------------------------------------------


def test_admin_lists_all_users_without_hashes(api, make_user):
    make_user("ana@brasaland.com")
    _, admin_headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    response = api.get(USERS, headers=admin_headers)
    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == ["ana@brasaland.com", "admin@brasaland.com"]
    assert all("hashed_password" not in user for user in response.json())


@pytest.mark.parametrize("role", [Role.USER, Role.MANAGER])
def test_non_admin_cannot_list_users(api, make_user, role):
    _, headers = make_user(role=role)
    response = api.get(USERS, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


# --- GET /users/{id} ------------------------------------------------------------------------


def test_user_reads_own_account(api, make_user):
    user, headers = make_user()
    response = api.get(f"{USERS}/{user.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == user.id and "hashed_password" not in response.json()


def test_user_cannot_read_another_account(api, make_user):
    other, _ = make_user("bea@brasaland.com")
    _, headers = make_user("ana@brasaland.com")
    assert api.get(f"{USERS}/{other.id}", headers=headers).status_code == 403


def test_non_admin_gets_403_even_if_id_does_not_exist(api, make_user):
    # No revela qué IDs existen.
    _, headers = make_user()
    assert api.get(f"{USERS}/no-existe", headers=headers).status_code == 403


def test_admin_reads_any_account_and_gets_404_for_missing(api, make_user):
    other, _ = make_user("bea@brasaland.com")
    _, admin_headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    assert api.get(f"{USERS}/{other.id}", headers=admin_headers).status_code == 200
    response = api.get(f"{USERS}/no-existe", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


# --- PUT /users/{id} ------------------------------------------------------------------------


def test_user_updates_own_email_and_password(api, make_user):
    user, headers = make_user()
    response = api.put(f"{USERS}/{user.id}", headers=headers, json={"email": "ana.maria@brasaland.com", "password": "nueva-clave-segura"})
    assert response.status_code == 200
    assert response.json()["email"] == "ana.maria@brasaland.com"
    assert api.post(LOGIN, json={"email": "ana.maria@brasaland.com", "password": "nueva-clave-segura"}).status_code == 200
    assert api.post(LOGIN, json={"email": "ana.maria@brasaland.com", "password": "parrilla-segura"}).status_code == 401


def test_user_cannot_update_another_account(api, make_user, auth_store):
    other, _ = make_user("bea@brasaland.com")
    _, headers = make_user("ana@brasaland.com")
    response = api.put(f"{USERS}/{other.id}", headers=headers, json={"email": "robada@brasaland.com"})
    assert response.status_code == 403
    assert service.get_user_by_id(auth_store, other.id).email == "bea@brasaland.com"


@pytest.mark.parametrize("payload", [{"role": "admin"}, {"is_active": False}])
def test_non_admin_cannot_change_role_or_status_even_own(api, make_user, payload):
    user, headers = make_user(role=Role.MANAGER)
    response = api.put(f"{USERS}/{user.id}", headers=headers, json=payload)
    assert response.status_code == 403
    assert "administrador" in response.json()["error"]["message"]


def test_admin_changes_role_and_status_of_another_user(api, make_user):
    other, _ = make_user("bea@brasaland.com")
    _, admin_headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    response = api.put(f"{USERS}/{other.id}", headers=admin_headers, json={"role": "manager", "is_active": False})
    assert response.status_code == 200
    assert response.json()["role"] == "manager" and response.json()["is_active"] is False


def test_update_invalid_role_is_422(api, make_user):
    _, admin_headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    response = api.put(f"{USERS}/x", headers=admin_headers, json={"role": "superadmin"})
    assert response.status_code == 422


def test_update_to_email_in_use_is_409(api, make_user):
    make_user("bea@brasaland.com")
    user, headers = make_user("ana@brasaland.com")
    response = api.put(f"{USERS}/{user.id}", headers=headers, json={"email": "bea@brasaland.com"})
    assert response.status_code == 409


def test_admin_update_missing_user_is_404(api, make_user):
    _, admin_headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    assert api.put(f"{USERS}/no-existe", headers=admin_headers, json={"is_active": True}).status_code == 404


def test_update_name_is_not_accepted_in_users(api, make_user):
    user, headers = make_user()
    assert api.put(f"{USERS}/{user.id}", headers=headers, json={"name": "Ana"}).status_code == 422


# --- DELETE /users/{id} ---------------------------------------------------------------------


def test_user_deletes_own_account_and_profile(api, make_user, auth_store):
    user, headers = make_user(name="Ana")
    response = api.delete(f"{USERS}/{user.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == user.id
    assert service.get_user_by_id(auth_store, user.id) is None
    assert auth_store.profiles.get_by_user_id(user.id) is None
    # Su token deja de servir.
    assert api.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_user_cannot_delete_another_account(api, make_user, auth_store):
    other, _ = make_user("bea@brasaland.com")
    _, headers = make_user("ana@brasaland.com")
    assert api.delete(f"{USERS}/{other.id}", headers=headers).status_code == 403
    assert service.get_user_by_id(auth_store, other.id) is not None


def test_admin_deletes_another_account_and_404_for_missing(api, make_user):
    other, _ = make_user("bea@brasaland.com")
    _, admin_headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    assert api.delete(f"{USERS}/{other.id}", headers=admin_headers).status_code == 200
    assert api.delete(f"{USERS}/{other.id}", headers=admin_headers).status_code == 404
