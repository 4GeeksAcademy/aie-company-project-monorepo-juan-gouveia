"""Utilidades de la batería unitaria del gestor de incidencias (no son fixtures)."""

from datetime import datetime, timezone

# Instante fijo para las incidencias creadas en el repositorio con `now`.
T0 = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)


def incident_data(**changes) -> dict:
    """Datos válidos de una incidencia (sin `status`: empieza en `open`); `changes` sustituye o añade campos."""
    return {
        "title": "Parrilla 2 sin gas",
        "description": "La parrilla 2 no enciende desde la apertura.",
        "category": "equipment_failure",
        "origin": "branch",
        "branch": "medellin_laureles",
        **changes,
    }
