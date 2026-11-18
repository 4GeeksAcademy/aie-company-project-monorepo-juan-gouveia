"""Errores del dominio de usuarios. El router los traduce a respuestas HTTP."""


class DuplicateEmailError(Exception):
    """Ya existe un usuario con ese email (sin distinguir mayúsculas)."""

    def __init__(self, email: str):
        super().__init__(email)
        self.email = email
