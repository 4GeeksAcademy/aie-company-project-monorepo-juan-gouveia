"""Inyección de fallos para la demo de reintentos y de la DLQ (decisión T12 del plan).

`TASKS_FAULT_INJECTION`, solo en el worker y vacía por defecto, hace fallar `telemetry.report` antes de
tocar la base:

- `transient`: todos los intentos fallan con un error transitorio → 4 ejecuciones → DLQ
  `max_retries_exceeded`.
- `transient:N`: fallan los N primeros intentos y el siguiente termina bien (el log con reintento).
- `permanent`: el primer intento falla sin reintento → DLQ `non_retryable`.

La API no la conoce y ninguna petición la activa. Se lee en cada ejecución, pero el worker toma el entorno
al arrancar: para cambiarla, se reinicia el worker. Un valor que no es ninguno de estos es un error de
configuración y hace fallar la tarea (permanente), en vez de ignorarse en silencio.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from brasaland_tasks.errors import InjectedPermanentFault, InjectedTransientFault

FAULT_INJECTION_ENV = "TASKS_FAULT_INJECTION"


class InvalidFaultInjection(ValueError):
    """TASKS_FAULT_INJECTION tiene un valor que no se reconoce."""


@dataclass(frozen=True)
class FaultPlan:
    kind: str  # "transient" o "permanent"
    # Intentos que fallan (desde 1); None = todos.
    failing_attempts: int | None = None

    def fails(self, attempt: int) -> bool:
        return self.failing_attempts is None or attempt <= self.failing_attempts


def parse_fault_injection(raw: str | None) -> FaultPlan | None:
    value = (raw or "").strip().lower()
    if not value:
        return None
    if value == "permanent":
        return FaultPlan("permanent")
    if value == "transient":
        return FaultPlan("transient")
    if value.startswith("transient:"):
        count = value.removeprefix("transient:")
        if count.isdigit() and int(count) >= 1:
            return FaultPlan("transient", int(count))
    raise InvalidFaultInjection(
        f"{FAULT_INJECTION_ENV}={raw!r} no es válido: usa transient, transient:N (N ≥ 1) o permanent."
    )


def current_plan() -> FaultPlan | None:
    return parse_fault_injection(os.environ.get(FAULT_INJECTION_ENV))


def inject_fault(attempt: int) -> None:
    """Lanza el fallo configurado para este intento, si hay uno. Sin variable, no hace nada."""
    plan = current_plan()
    if plan is None or not plan.fails(attempt):
        return
    if plan.kind == "permanent":
        raise InjectedPermanentFault(f"Fallo permanente inyectado ({FAULT_INJECTION_ENV}), intento {attempt}.")
    raise InjectedTransientFault(f"Fallo transitorio inyectado ({FAULT_INJECTION_ENV}), intento {attempt}.")
