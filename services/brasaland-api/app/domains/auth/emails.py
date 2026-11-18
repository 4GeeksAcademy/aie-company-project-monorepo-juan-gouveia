"""Correo de restablecimiento de contraseña (decisión P-8 de AUTH-03).

HTML con estilos en línea (los clientes de correo ignoran las hojas de estilo), una sola columna de
600 px como máximo y un botón grande, para que se lea bien en móvil. Se envía también en texto plano.
"""

from html import escape

from app.core.email import EmailMessage

SUBJECT = "Restablece tu contraseña de Brasaland"


def build_password_reset_email(to: str, name: str | None, link: str, expire_minutes: int) -> EmailMessage:
    greeting = f"Hola, {name}:" if name else "Hola:"
    text = (
        f"{greeting}\n\n"
        "Recibimos una solicitud para restablecer la contraseña de tu cuenta del backoffice de Brasaland.\n\n"
        f"Abre este enlace para elegir una contraseña nueva (caduca en {expire_minutes} minutos y solo "
        f"sirve una vez):\n{link}\n\n"
        "Si no lo pediste, ignora este correo: tu contraseña no cambiará.\n\n"
        "Brasaland\n"
    )

    safe_link = escape(link, quote=True)
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(SUBJECT)}</title>
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f4f6;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background-color:#ffffff;border:1px solid #fecaca;border-radius:8px;">
<tr><td style="padding:24px;font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.5;color:#111827;">
<p style="margin:0 0 16px;font-size:20px;font-weight:bold;color:#b91c1c;">Brasaland</p>
<p style="margin:0 0 16px;">{escape(greeting)}</p>
<p style="margin:0 0 24px;">Recibimos una solicitud para restablecer la contraseña de tu cuenta del backoffice de Brasaland.</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
<tr><td style="border-radius:6px;background-color:#b91c1c;">
<a href="{safe_link}" style="display:inline-block;padding:14px 28px;font-family:Arial,Helvetica,sans-serif;font-size:16px;font-weight:bold;color:#ffffff;text-decoration:none;border-radius:6px;">Restablecer contraseña</a>
</td></tr>
</table>
<p style="margin:0 0 8px;">El enlace caduca en {expire_minutes} minutos y solo sirve una vez. Si el botón no funciona, copia esta dirección en tu navegador:</p>
<p style="margin:0 0 24px;word-break:break-all;font-size:14px;"><a href="{safe_link}" style="color:#b91c1c;">{safe_link}</a></p>
<p style="margin:0;font-size:14px;color:#4b5563;">Si no lo pediste, ignora este correo: tu contraseña no cambiará.</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""
    return EmailMessage(to=to, subject=SUBJECT, html=html, text=text)
