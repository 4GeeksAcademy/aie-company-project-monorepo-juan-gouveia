"""Registro de los enlaces de restablecimiento de contraseña (ticket AUTH-03).

El token del enlace es un JWT firmado, pero un JWT no se puede invalidar por sí solo. Cada token
tiene aquí una fila, identificada por su `jti`: al usarse se marca `used_at`, y ya no vale aunque
siga sin caducar. La tabla también sirve para limitar las solicitudes por usuario y hora.
"""

from datetime import datetime

from pydantic import BaseModel


class PasswordReset(BaseModel):
    id: str  # `jti` del token
    user_id: str
    created_at: datetime
    expires_at: datetime
    # Cuándo se usó o se anuló (por otro restablecimiento o un cambio de contraseña); None si sigue pendiente.
    used_at: datetime | None = None
