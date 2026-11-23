"""Disparo manual del pipeline (`POST /reporting/pipeline-runs`; diseño, §6.3; decisión I1).

La API nunca ejecuta el ETL: registra la corrida en `pending` y le pide a Prefect un flow run del
deployment `weekly-location-performance/weekly`, sin esperar. Lo ejecuta el proceso
`python data/pipelines/pipeline.py --serve`, que pasa la corrida a `running` y la cierra.

Este módulo no importa Prefect (ver `runs.py`): habla con su API REST (`PREFECT_API_URL`) con httpx, con
las mismas dos llamadas que hace `run_deployment(..., timeout=0)`: buscar el deployment por nombre y
crear un flow run con los parámetros.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import httpx
from brasaland_pipelines import repository
from brasaland_pipelines.runs import (
    DEFAULT_STALE_RUN_MINUTES,
    DEPLOYMENT,
    DEPLOYMENT_NAME,
    FLOW_NAME,
    InvalidWeekRange,
    compute_weeks,
)
from sqlalchemy import Engine

PREFECT_API_URL_ENV = "PREFECT_API_URL"
PREFECT_TIMEOUT_SECONDS = 10

__all__ = ["DEPLOYMENT", "InvalidWeekRange", "OrchestratorUnavailable", "trigger_pipeline_run"]


class OrchestratorUnavailable(RuntimeError):
    """Prefect no está configurado, no respondió o no tiene el deployment (503 en la API)."""


def prefect_api_url() -> str | None:
    """URL de la API del servidor de Prefect, p. ej. `http://prefect-server:4200/api`."""
    return os.environ.get(PREFECT_API_URL_ENV, "").strip().rstrip("/") or None


def create_flow_run(parameters: dict[str, Any], *, client: httpx.Client | None = None) -> UUID:
    """Crea un flow run del deployment con esos parámetros, sin esperar a que corra. Devuelve su id."""
    base_url = prefect_api_url()
    if base_url is None:
        raise OrchestratorUnavailable(f"{PREFECT_API_URL_ENV} no está configurada: no hay servidor de Prefect al que pedir la corrida.")
    http = client or httpx.Client(timeout=PREFECT_TIMEOUT_SECONDS)
    try:
        found = http.get(f"{base_url}/deployments/name/{FLOW_NAME}/{DEPLOYMENT_NAME}")
        if found.status_code == 404:
            raise OrchestratorUnavailable(
                f"El deployment {DEPLOYMENT} no está registrado: arranca `python data/pipelines/pipeline.py --serve`."
            )
        found.raise_for_status()
        created = http.post(f"{base_url}/deployments/{found.json()['id']}/create_flow_run", json={"parameters": parameters})
        created.raise_for_status()
        return UUID(created.json()["id"])
    except httpx.HTTPError as error:
        raise OrchestratorUnavailable(f"Prefect no respondió: {type(error).__name__}.") from error
    finally:
        if client is None:
            http.close()


def trigger_pipeline_run(
    engine: Engine,
    *,
    week_from: date | None = None,
    week_to: date | None = None,
    requested_by: UUID | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Registra una corrida manual y la pone en la cola de Prefect. Devuelve la corrida en `pending`.

    Sin rango, las 4 últimas semanas cerradas; con rango, un backfill (valores del diseño, `runs.py`).
    Errores:
    - `InvalidWeekRange`: el rango no es válido (no son lunes, está al revés, incluye la semana en
      curso o pasa del máximo);
    - `repository.PipelineRunInProgress`: ya hay una corrida activa;
    - `OrchestratorUnavailable`: Prefect no está configurado, no respondió o no tiene el deployment; si
      la corrida ya estaba registrada, queda en `failed` con ese error.
    """
    if prefect_api_url() is None:
        raise OrchestratorUnavailable(f"{PREFECT_API_URL_ENV} no está configurada: no hay servidor de Prefect al que pedir la corrida.")

    now = datetime.now(UTC)
    weeks = compute_weeks(today or now.date(), week_from, week_to)

    with engine.begin() as conn:
        repository.abandon_stale_runs(conn, now=now, stale_minutes=DEFAULT_STALE_RUN_MINUTES)
        run_id = repository.create_pending_run(
            conn, week_from=weeks[0], week_to=weeks[-1], requested_by=requested_by, now=now
        )

    parameters = {"week_from": weeks[0].isoformat(), "week_to": weeks[-1].isoformat(), "trigger": "manual", "run_id": str(run_id)}
    try:
        flow_run_id = create_flow_run(parameters)
    except OrchestratorUnavailable as error:
        with engine.begin() as conn:
            repository.finish_run(
                conn, run_id, status="failed", now=datetime.now(UTC), error_message=f"orchestrator_unavailable: {error}"[:500]
            )
        raise

    with engine.begin() as conn:
        repository.set_prefect_flow_run_id(conn, run_id, flow_run_id)
        return repository.read_pipeline_run(conn, run_id)
