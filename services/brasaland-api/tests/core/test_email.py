"""Emisores de correo (AUTH-03). Ninguna prueba llama a Resend: su SDK se sustituye."""

import logging

import pytest
import resend

from app.core.config import get_settings
from app.core.email import (
    DisabledEmailSender,
    EmailMessage,
    EmailSendError,
    ResendEmailSender,
    get_email_sender,
    send_safely,
)
from app.domains.auth.emails import build_password_reset_email

MESSAGE = EmailMessage(to="ana@brasaland.com", subject="Asunto", html="<p>Hola</p>", text="Hola")


def test_without_api_key_the_sender_is_disabled(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    get_settings.cache_clear()
    assert isinstance(get_email_sender(), DisabledEmailSender)


def test_with_api_key_the_sender_is_resend(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_clave_de_prueba")
    get_settings.cache_clear()
    assert isinstance(get_email_sender(), ResendEmailSender)


def test_disabled_sender_logs_without_recipient_or_body(caplog):
    with caplog.at_level(logging.WARNING):
        DisabledEmailSender().send(MESSAGE)
    assert "RESEND_API_KEY" in caplog.text
    assert MESSAGE.to not in caplog.text and MESSAGE.text not in caplog.text


def test_resend_sender_sends_html_and_text(monkeypatch):
    calls = []
    monkeypatch.setattr(resend.Emails, "send", lambda params, options=None: calls.append(params) or {"id": "1"})
    ResendEmailSender("re_clave_de_prueba", "Brasaland <onboarding@resend.dev>").send(MESSAGE)
    (params,) = calls
    assert params == {
        "from": "Brasaland <onboarding@resend.dev>",
        "to": ["ana@brasaland.com"],
        "subject": "Asunto",
        "html": "<p>Hola</p>",
        "text": "Hola",
    }
    assert resend.api_key == "re_clave_de_prueba"


def test_resend_errors_become_email_send_error_without_details(monkeypatch):
    def fail(params, options=None):
        raise RuntimeError("You can only send testing emails to your own email address (ana@brasaland.com)")

    monkeypatch.setattr(resend.Emails, "send", fail)
    with pytest.raises(EmailSendError) as error:
        ResendEmailSender("re_clave_de_prueba", "Brasaland <onboarding@resend.dev>").send(MESSAGE)
    assert "ana@brasaland.com" not in str(error.value)


def test_send_safely_swallows_and_logs_failures(caplog):
    class Failing:
        def send(self, message):
            raise EmailSendError("Resend rechazó el envío (ResendError).")

    with caplog.at_level(logging.ERROR):
        send_safely(Failing(), MESSAGE)
    assert "No se pudo enviar" in caplog.text
    assert MESSAGE.to not in caplog.text


# --- Plantilla del correo (P-8) -------------------------------------------------------------

LINK = "http://localhost:3001/reset-password?token=abc.def.ghi"


def test_reset_email_has_link_in_html_and_text():
    message = build_password_reset_email("ana@brasaland.com", "Ana", LINK, 30)
    assert message.to == "ana@brasaland.com"
    assert message.subject == "Restablece tu contraseña de Brasaland"
    assert LINK in message.text and f'href="{LINK}"' in message.html
    assert "30 minutos" in message.text and "30 minutos" in message.html
    assert "Hola, Ana:" in message.text


def test_reset_email_is_mobile_friendly():
    html = build_password_reset_email("ana@brasaland.com", None, LINK, 30).html
    assert 'name="viewport"' in html
    assert "max-width:600px" in html
    assert "<style" not in html  # estilos en línea: muchos clientes ignoran las hojas de estilo


def test_reset_email_without_name_and_escapes_html():
    message = build_password_reset_email("ana@brasaland.com", "<b>Ana</b>", LINK, 30)
    assert "&lt;b&gt;Ana&lt;/b&gt;" in message.html and "<b>Ana</b>" not in message.html
    assert build_password_reset_email("ana@brasaland.com", None, LINK, 30).text.startswith("Hola:")
