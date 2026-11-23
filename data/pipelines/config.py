"""Configuración y credenciales del pipeline (diseño, §5.5; decisión I2).

- **Conexión:** el bloque `Secret` `brasaland-reporting-db` y, si no existe o Prefect no lo encuentra,
  la variable de entorno `REPORTING_DATABASE_URL`. Es la cadena del rol `reporting_pipeline`
  (migración 005): lee `telemetry_events` y `locations` y solo escribe en `reporting.*`.
- **Parámetros:** el bloque `weekly-location-performance-config` y, si no existe, los valores del diseño.

Así el pipeline corre con un servidor de Prefect que tenga los bloques registrados y también como script
suelto, solo con el `.env`. El flow registra en su log qué fuente usó.
"""

from __future__ import annotations

import os

from prefect.blocks.core import Block
from prefect.blocks.system import Secret

SECRET_BLOCK = "brasaland-reporting-db"
CONFIG_BLOCK = "weekly-location-performance-config"
DATABASE_URL_ENV = "REPORTING_DATABASE_URL"


class ConfigError(RuntimeError):
    """Falta la conexión del pipeline: ni el bloque ni la variable de entorno."""


class WeeklyLocationPerformanceConfig(Block):
    """Parámetros del pipeline del Reporte Semanal de Costo y Merma por Local (diseño, §5.5)."""

    _block_type_name = "Weekly Location Performance Config"
    _description = "Parámetros del pipeline del Reporte Semanal de Costo y Merma por Local."

    # Solo los eventos de este entorno entran en los KPIs (riesgo R7 del plan de telemetría).
    environment: str = "production"
    # Semanas cerradas que recalcula cada corrida, para absorber los eventos que llegan tarde.
    lookback_weeks: int = 4
    # Semanas máximas de un backfill por rango.
    max_backfill_weeks: int = 26
    # Una corrida activa más allá de este tiempo se da por abandonada (el flow tiene 30 min de límite).
    stale_run_minutes: int = 30


def load_settings() -> tuple[WeeklyLocationPerformanceConfig, str]:
    """Los parámetros del bloque, o los valores del diseño si el bloque no está registrado."""
    try:
        return WeeklyLocationPerformanceConfig.load(CONFIG_BLOCK), f"bloque {CONFIG_BLOCK}"
    except Exception:  # noqa: BLE001 — sin bloque (o sin servidor) se usan los valores por defecto
        return WeeklyLocationPerformanceConfig(), "valores por defecto"


def load_database_url() -> tuple[str, str]:
    """La cadena de conexión y de dónde salió. Nunca se registra la cadena, solo su fuente."""
    try:
        return Secret.load(SECRET_BLOCK).get(), f"bloque {SECRET_BLOCK}"
    except Exception:  # noqa: BLE001 — sin bloque (o sin servidor), la variable de entorno
        url = os.environ.get(DATABASE_URL_ENV, "").strip()
        if url:
            return url, f"variable {DATABASE_URL_ENV}"
    raise ConfigError(
        f"Falta la conexión del pipeline: registra el bloque Secret '{SECRET_BLOCK}' o define "
        f"{DATABASE_URL_ENV} (cadena del rol reporting_pipeline, ver data/pipelines/.env.example)."
    )


def register_blocks() -> list[str]:
    """Registra los dos bloques en Prefect: la conexión desde `REPORTING_DATABASE_URL` y los parámetros
    con los valores del diseño (`python pipeline.py --register-blocks`). Sobrescribe los que existan."""
    url = os.environ.get(DATABASE_URL_ENV, "").strip()
    if not url:
        raise ConfigError(f"Define {DATABASE_URL_ENV} antes de registrar el bloque '{SECRET_BLOCK}'.")
    Secret(value=url).save(SECRET_BLOCK, overwrite=True)
    WeeklyLocationPerformanceConfig().save(CONFIG_BLOCK, overwrite=True)
    return [SECRET_BLOCK, CONFIG_BLOCK]
