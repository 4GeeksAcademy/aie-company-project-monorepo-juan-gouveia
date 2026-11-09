"""Envío de correos transaccionales (ticket AUTH-03).

El resto de la API solo conoce `EmailMessage` y `EmailSender`. El proveedor concreto (Resend,
elegido frente a SendGrid; ver docs/BRIEFING_DIVERGENCES.md) se elige aquí según la configuración,
y las pruebas lo sustituyen por un emisor falso con `app.dependency_overrides[get_email_sender]`.

Sin RESEND_API_KEY, el emisor está desactivado: no envía nada y lo registra en el log, sin el
contenido del mensaje (que puede llevar un enlace de restablecimiento).
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import resend

from app.core.config import get_settings

logger = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str


class EmailSendError(Exception):
    """El proveedor rechazó el envío o no respondió."""


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Envía el mensaje; lanza EmailSendError si falla."""


class DisabledEmailSender:
    """Sin RESEND_API_KEY: no envía y lo deja en el log (sin el enlace, que es una credencial)."""

    def send(self, message: EmailMessage) -> None:
        logger.warning(
            "Envío de correos desactivado (falta RESEND_API_KEY): no se envió «%s».", message.subject
        )


# Tiempo máximo de cada envío a Resend. El SDK ya usa 30 s por defecto (RequestsClient); se fija
# aquí para no depender de ese valor. El envío va en segundo plano y Resend suele responder en
# menos de un segundo, así que 10 s liberan antes el hilo si Resend no responde.
RESEND_TIMEOUT_SECONDS = 10


class ResendEmailSender:
    """Envía con Resend (SDK oficial `resend`).

    Sin dominio verificado, el remitente es `onboarding@resend.dev` y Resend solo entrega al email
    de la cuenta: a cualquier otro destinatario responde 403, que aquí se convierte en EmailSendError.
    """

    def __init__(self, api_key: str, sender: str):
        self._api_key = api_key
        self._sender = sender

    def send(self, message: EmailMessage) -> None:
        # El SDK lee la clave y el cliente HTTP de variables de módulo; se fijan en cada envío.
        resend.api_key = self._api_key
        resend.default_http_client = resend.RequestsClient(timeout=RESEND_TIMEOUT_SECONDS)
        params: resend.Emails.SendParams = {
            "from": self._sender,
            "to": [message.to],
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
        }
        try:
            resend.Emails.send(params)
        except Exception as error:  # noqa: BLE001 - errores de la API de Resend o de red
            raise EmailSendError(f"Resend rechazó el envío ({describe_resend_error(error)}).") from None


def describe_resend_error(error: Exception) -> str:
    """Lo que se puede registrar de un fallo de Resend: el tipo, el estado HTTP y su tipo de error.

    Nunca el mensaje: el de Resend puede incluir el destinatario (por ejemplo, en el 403 de
    «solo puedes enviar a tu propio email»). Por eso EmailSendError se lanza `from None`: con la causa
    encadenada, logger.exception imprimiría ese mensaje en el traceback.
    """
    parts = [type(error).__name__]
    if isinstance(error, resend.exceptions.ResendError):
        parts += [f"HTTP {error.code}", str(error.error_type)]
    return ", ".join(parts)


def get_email_sender() -> EmailSender:
    """Dependencia de FastAPI: Resend si hay RESEND_API_KEY; si no, el emisor desactivado."""
    settings = get_settings()
    if settings.resend_api_key is None:
        return DisabledEmailSender()
    return ResendEmailSender(settings.resend_api_key, settings.email_from)


def send_safely(sender: EmailSender, message: EmailMessage) -> None:
    """Envía sin propagar errores: se usa en segundo plano, cuando la respuesta ya salió.

    Un fallo (por ejemplo, el 403 de Resend con un destinatario no permitido) solo se registra.
    No se registra el destinatario: el log no debe servir para saber qué emails están registrados.
    """
    try:
        sender.send(message)
    except Exception:  # noqa: BLE001 - cualquier fallo del proveedor se registra y se descarta
        logger.exception("No se pudo enviar el correo «%s».", message.subject)
