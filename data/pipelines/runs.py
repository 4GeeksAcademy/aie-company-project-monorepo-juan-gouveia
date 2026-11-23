"""Reglas de las corridas que no dependen de Prefect: nombres, valores por defecto y semanas.

Las usan el flow (`pipeline.py`) y el disparo desde la API (`trigger.py`). La API no puede importar
Prefect: al importarse, Prefect configura el logging del proceso (el logger raíz y el de uvicorn) y
cambiaría los logs de la API. Por eso este módulo, `repository.py` y `trigger.py` no lo importan.
"""

from __future__ import annotations

from datetime import date, timedelta

FLOW_NAME = "weekly-location-performance"
DEPLOYMENT_NAME = "weekly"
DEPLOYMENT = f"{FLOW_NAME}/{DEPLOYMENT_NAME}"

# Valores del diseño (§5.5). El bloque `weekly-location-performance-config` puede cambiarlos para el
# flow; la API calcula con estos el rango por defecto de una corrida manual.
DEFAULT_ENVIRONMENT = "production"
DEFAULT_LOOKBACK_WEEKS = 4
DEFAULT_MAX_BACKFILL_WEEKS = 26
DEFAULT_STALE_RUN_MINUTES = 30


class InvalidWeekRange(ValueError):
    """El rango de semanas pedido no se puede calcular (422 `invalid_week_range` en la API)."""


def compute_weeks(
    today: date,
    week_from: date | None,
    week_to: date | None,
    lookback_weeks: int = DEFAULT_LOOKBACK_WEEKS,
    max_backfill_weeks: int = DEFAULT_MAX_BACKFILL_WEEKS,
    include_current_week: bool = False,
) -> list[date]:
    """Los lunes que recalcula una corrida (diseño, §3.4).

    Sin rango, las `lookback_weeks` últimas semanas ISO cerradas. Con rango, un backfill: lunes,
    `week_from ≤ week_to`, sin la semana en curso y como mucho `max_backfill_weeks`. La semana en curso
    solo entra con `include_current_week` (verificación; la corrida programada nunca la usa).
    """
    current_week = today - timedelta(days=today.weekday())
    last_allowed = current_week if include_current_week else current_week - timedelta(days=7)

    if week_from is None and week_to is None:
        first = current_week - timedelta(days=7 * lookback_weeks)
        week_from, week_to = first, last_allowed
    else:
        week_from = week_from or week_to
        week_to = week_to or week_from
        if week_from.weekday() != 0 or week_to.weekday() != 0:
            raise InvalidWeekRange("week_from y week_to deben ser lunes (week_start de la semana ISO).")
        if week_from > week_to:
            raise InvalidWeekRange("week_from no puede ser posterior a week_to.")
        if week_to > last_allowed:
            raise InvalidWeekRange("La semana en curso todavía no está cerrada: no se calcula.")

    weeks = [week_from + timedelta(days=7 * i) for i in range((week_to - week_from).days // 7 + 1)]
    if len(weeks) > max_backfill_weeks:
        raise InvalidWeekRange(f"El rango tiene {len(weeks)} semanas; el máximo es {max_backfill_weeks}.")
    return weeks
