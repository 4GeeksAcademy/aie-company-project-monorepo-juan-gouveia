"""`GET /auth/me`: la ruta `read_me` con el usuario que entrega `get_current_user`."""

from app.core.security import create_access_token
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.router import read_me
from app.domains.users import service as user_service
from app.domains.users.models import Role
from tests.auth.helpers import raises_api_error


def test_me_f1_returns_token_user_with_profile(auth_store, user_factory):
    user = user_factory("lucia@brasaland.com", role=Role.MANAGER, name="Lucía Pérez", phone="+57 300 000 0000")

    me = read_me(user=user, store=auth_store)

    assert (me.id, me.email, me.role) == (user.id, "lucia@brasaland.com", Role.MANAGER)
    assert me.profile is not None
    assert (me.profile.user_id, me.profile.name, me.profile.phone) == (user.id, "Lucía Pérez", "+57 300 000 0000")


def test_me_l1_user_without_profile_gets_empty_profile(auth_store, active_user):
    auth_store.profiles.delete_for_user(active_user.id)

    me = read_me(user=active_user, store=auth_store)

    assert me.id == active_user.id
    assert me.profile is None


def test_me_x1_token_of_deleted_user_never_reaches_route(auth_store, active_user, clock):
    token = create_access_token(active_user.id, now=clock.now)
    user_service.delete_user(auth_store, active_user.id)

    # La ruta solo recibe al usuario a través de get_current_user, que corta antes.
    with raises_api_error(401, "invalid_token"):
        get_current_user(token=token, store=auth_store)
