"""Errores del dominio de incidentes.

Los errores del archivo CSV están en el paquete compartido (`brasaland_shared.incidents.exceptions`),
porque también los usan los scripts; aquí se reexportan para el router del analizador.
El router los traduce a respuestas HTTP con mensajes en español.
"""

from brasaland_shared.incidents.exceptions import (
    EmptyFileError,
    IncidentFileError,
    InvalidEncodingError,
    MalformedCsvError,
    MissingColumnsError,
    NoRecordsError,
)

__all__ = [
    "EmptyFileError",
    "IncidentFileError",
    "InvalidEncodingError",
    "InvalidTransitionError",
    "MalformedCsvError",
    "MissingColumnsError",
    "NoRecordsError",
]


class InvalidTransitionError(ValueError):
    """Cambio de estado que el ciclo de vida del gestor de incidencias no permite."""

    def __init__(self, current, target, allowed):
        self.current = current
        self.target = target
        self.allowed = allowed
        super().__init__(f"Invalid transition: {current} -> {target}")
