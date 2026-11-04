"""GET y PUT /profiles/me: cada usuario solo ve y modifica su propio perfil."""

import pytest

ME = "/api/v1/profiles/me"


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
