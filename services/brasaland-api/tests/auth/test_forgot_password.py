"""`POST /auth/forgot-password`: la ruta `forgot_password` y `passwords.request_password_reset`.

La ruta responde siempre lo mismo; lo que se comprueba es si crea el enlace y programa el correo.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import BackgroundTasks

from app.core.email import send_safely
from app.domains.auth import passwords
from app.domains.auth.router import forgot_password
from app.domains.auth.schemas import FORGOT_PASSWORD_MESSAGE, ForgotPasswordRequest
from tests.auth.helpers import token_from_email

pytestmark = pytest.mark.anyio

EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)


def resets_of(store, user) -> int:
    return store.password_resets.count_created_since(user.id, EPOCH)


async def call_route(store, email_sender, settings, email: str):
    tasks = BackgroundTasks()
    response = await forgot_password(
        ForgotPasswordRequest(email=email), tasks, store=store, sender=email_sender, settings=settings
    )
    return response, tasks.tasks


# --- Camino feliz ---------------------------------------------------------------------------


async def test_fgt_f1_active_account_gets_link_and_scheduled_email(auth_store, email_sender, auth_settings, user_factory):
    user = user_factory("ana@brasaland.com", name="Ana Gómez")

    response, tasks = await call_route(auth_store, email_sender, auth_settings, user.email)

    assert response.message == FORGOT_PASSWORD_MESSAGE
    assert resets_of(auth_store, user) == 1
    # El correo sale en segundo plano, con el emisor inyectado.
    assert len(tasks) == 1
    assert tasks[0].func is send_safely
    sender, message = tasks[0].args
    assert sender is email_sender
    assert message.to == user.email
    assert "Ana Gómez" in message.text
    assert f"{auth_settings.frontend_url}/reset-password?token=" in message.text
    assert token_from_email(message.text)


def test_fgt_f1_link_expires_after_configured_minutes(auth_store, auth_settings, active_user, clock):
    request = passwords.request_password_reset(auth_store, active_user.email, auth_settings, now=clock.now)

    assert request.reset.user_id == active_user.id
    assert request.reset.expires_at - request.reset.created_at == timedelta(
        minutes=auth_settings.password_reset_expire_minutes
    )
    assert request.reset.used_at is None


# --- Casos límite ---------------------------------------------------------------------------


def test_fgt_l1_fourth_request_in_an_hour_is_ignored_until_hour_passes(auth_store, auth_settings, active_user, clock):
    for _ in range(passwords.MAX_RESET_REQUESTS_PER_HOUR):
        assert passwords.request_password_reset(auth_store, active_user.email, auth_settings, now=clock.now)
        clock.advance(minutes=1)

    assert passwords.request_password_reset(auth_store, active_user.email, auth_settings, now=clock.now) is None
    assert resets_of(auth_store, active_user) == 3

    # La primera se pidió hace 3 minutos; una hora después de ella vuelve a haber hueco.
    clock.advance(minutes=57, seconds=1)
    assert passwords.request_password_reset(auth_store, active_user.email, auth_settings, now=clock.now)
    assert resets_of(auth_store, active_user) == 4


async def test_fgt_l1_route_answers_the_same_when_limit_is_reached(auth_store, email_sender, auth_settings, active_user):
    for _ in range(passwords.MAX_RESET_REQUESTS_PER_HOUR):
        await call_route(auth_store, email_sender, auth_settings, active_user.email)

    response, tasks = await call_route(auth_store, email_sender, auth_settings, active_user.email)

    assert response.message == FORGOT_PASSWORD_MESSAGE
    assert tasks == []


async def test_fgt_l2_uppercase_email_finds_account(auth_store, email_sender, auth_settings, active_user):
    _, tasks = await call_route(auth_store, email_sender, auth_settings, "  ANA@Brasaland.COM ")

    assert len(tasks) == 1
    assert tasks[0].args[1].to == active_user.email


def test_fgt_l2_user_without_profile_gets_email_without_name(auth_store, auth_settings, active_user, clock):
    auth_store.profiles.delete_for_user(active_user.id)

    request = passwords.request_password_reset(auth_store, active_user.email, auth_settings, now=clock.now)

    assert request.message.text.startswith("Hola:")


# --- Modos de fallo -------------------------------------------------------------------------


async def test_fgt_x1_unknown_email_and_inactive_account_get_same_answer_and_nothing_sent(
    auth_store, email_sender, auth_settings, active_user, inactive_user
):
    known, _ = await call_route(auth_store, email_sender, auth_settings, active_user.email)
    unknown, unknown_tasks = await call_route(auth_store, email_sender, auth_settings, "nadie@brasaland.com")
    inactive, inactive_tasks = await call_route(auth_store, email_sender, auth_settings, inactive_user.email)

    assert unknown.message == inactive.message == known.message == FORGOT_PASSWORD_MESSAGE
    assert unknown_tasks == inactive_tasks == []
    assert resets_of(auth_store, inactive_user) == 0
    assert email_sender.sent == []  # nada se envía en la propia petición
