"""GET y PUT /profiles/me y /profiles/{user_id}: cada usuario solo ve y modifica su propio perfil
(un admin puede leer cualquiera, pero no modificarlo)."""

import pytest

from app.domains.users.models import Role

ME = "/api/v1/profiles/me"
PROFILES = "/api/v1/profiles"


def test_get_my_profile(api, make_user):
    user, headers = make_user(name="Ana", phone="+57 300", address="Medellín")
    response = api.get(ME, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user.id
    assert (body["name"], body["phone"], body["address"]) == ("Ana", "+57 300", "Medellín")


def test_update_my_profile_only_sent_fields(api, make_user):
    _, headers = make_user(name="Ana", phone="+57 300", address="Medellín")
    response = api.put(ME, headers=headers, json={"name": "Ana María", "address": None})
    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["phone"], body["address"]) == ("Ana María", "+57 300", None)
    assert api.get(ME, headers=headers).json() == body


def test_update_only_changes_own_profile(api, make_user, auth_store):
    other, _ = make_user("bea@brasaland.com", name="Bea")
    _, headers = make_user("ana@brasaland.com", name="Ana")
    api.put(ME, headers=headers, json={"name": "Cambiado"})
    assert auth_store.profiles.get_by_user_id(other.id).name == "Bea"


def test_cannot_move_profile_to_another_user(api, make_user):
    other, _ = make_user("bea@brasaland.com")
    _, headers = make_user("ana@brasaland.com")
    response = api.put(ME, headers=headers, json={"user_id": other.id})
    assert response.status_code == 422


@pytest.mark.parametrize("payload", [{}, {"name": ""}, {"email": "a@b.co"}])
def test_invalid_update_is_422(api, make_user, payload):
    _, headers = make_user()
    assert api.put(ME, headers=headers, json=payload).status_code == 422


@pytest.mark.parametrize("method", ["get", "put"])
def test_profile_routes_without_token_are_401(api, method):
    kwargs = {"json": {"name": "Ana"}} if method == "put" else {}
    response = getattr(api, method)(ME, **kwargs)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_user_without_profile_gets_404(api, make_user, auth_store):
    user, headers = make_user()
    auth_store.profiles.delete_for_user(user.id)
    assert api.get(ME, headers=headers).json()["error"]["code"] == "profile_not_found"
    assert api.put(ME, headers=headers, json={"name": "Ana"}).status_code == 404


# --- /profiles/{user_id} ----------------------------------------------------------------------


def test_owner_reads_and_updates_profile_by_id(api, make_user):
    user, headers = make_user(name="Ana")
    assert api.get(f"{PROFILES}/{user.id}", headers=headers).json()["name"] == "Ana"
    response = api.put(f"{PROFILES}/{user.id}", headers=headers, json={"phone": "+57 300"})
    assert response.status_code == 200
    assert response.json()["phone"] == "+57 300" and response.json()["name"] == "Ana"


def test_user_cannot_read_another_profile(api, make_user):
    other, _ = make_user("bea@brasaland.com", name="Bea")
    _, headers = make_user("ana@brasaland.com")
    response = api.get(f"{PROFILES}/{other.id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_user_cannot_update_another_profile(api, make_user, auth_store):
    other, _ = make_user("bea@brasaland.com", name="Bea")
    _, headers = make_user("ana@brasaland.com")
    response = api.put(f"{PROFILES}/{other.id}", headers=headers, json={"name": "Cambiado"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert auth_store.profiles.get_by_user_id(other.id).name == "Bea"


def test_non_admin_gets_403_even_if_id_does_not_exist(api, make_user):
    _, headers = make_user()
    assert api.get(f"{PROFILES}/no-existe", headers=headers).status_code == 403
    assert api.put(f"{PROFILES}/no-existe", headers=headers, json={"name": "X"}).status_code == 403


def test_admin_reads_any_profile_but_cannot_modify_it(api, make_user, auth_store):
    other, _ = make_user("bea@brasaland.com", name="Bea")
    _, admin_headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    assert api.get(f"{PROFILES}/{other.id}", headers=admin_headers).json()["name"] == "Bea"
    # "Solo el dueño del perfil puede modificarlo": también frente a un admin.
    response = api.put(f"{PROFILES}/{other.id}", headers=admin_headers, json={"name": "Cambiado"})
    assert response.status_code == 403
    assert auth_store.profiles.get_by_user_id(other.id).name == "Bea"


def test_admin_gets_404_for_missing_profile(api, make_user):
    _, admin_headers = make_user("admin@brasaland.com", role=Role.ADMIN)
    response = api.get(f"{PROFILES}/no-existe", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "profile_not_found"


def test_me_is_not_taken_as_an_id(api, make_user):
    user, headers = make_user(name="Ana")
    assert api.get(ME, headers=headers).json()["user_id"] == user.id


def test_update_by_id_validates_body(api, make_user):
    user, headers = make_user()
    assert api.put(f"{PROFILES}/{user.id}", headers=headers, json={"user_id": "otro"}).status_code == 422


@pytest.mark.parametrize("method", ["get", "put"])
def test_profile_by_id_without_token_is_401(api, make_user, method):
    user, _ = make_user()
    kwargs = {"json": {"name": "Ana"}} if method == "put" else {}
    response = getattr(api, method)(f"{PROFILES}/{user.id}", **kwargs)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
