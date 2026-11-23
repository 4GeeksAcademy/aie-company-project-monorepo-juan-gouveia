"""Pipeline del "Reporte Semanal de Costo y Merma por Local" (diseño: data/pipelines/PIPELINE_DESIGN.md).

Lee `telemetry_events` y `locations` en solo lectura, calcula por local y semana ISO los cinco KPIs del
briefing y los escribe con upsert en `reporting.weekly_location_performance`. Cada corrida queda en
`reporting.pipeline_runs`. Nunca escribe en `telemetry_events` ni toca el reporte técnico.

Frecuencia: los lunes a las 06:00 America/Bogota (11:00 UTC), sobre las 4 últimas semanas cerradas.

Ejecución (desde data/pipelines/, con su entorno de uv; o `python data/pipelines/pipeline.py` con ese
entorno activado):

    uv run python pipeline.py                                   # una corrida: las 4 últimas semanas cerradas
    uv run python pipeline.py --week-from 2026-09-07 --week-to 2026-11-16   # backfill por rango
    uv run python pipeline.py --environment development --include-current-week   # verificación en local
    uv run python pipeline.py --register-blocks                 # registra los bloques de Prefect desde .env
    uv run python pipeline.py --serve                           # deployment de los lunes (necesita PREFECT_API_URL)

La conexión sale del bloque `brasaland-reporting-db` o de `REPORTING_DATABASE_URL` (ver config.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import UTC, date, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from brasaland_pipelines import config, repository
from brasaland_process.weekly_location_performance import (
    WeeklyPerformanceResult,
    build_weekly_location_performance,
)
from prefect import flow, get_run_logger, task
from prefect.context import TaskRunContext
from prefect.runtime import flow_run as current_flow_run
from prefect.schedules import Cron
from sqlalchemy import Engine
from sqlalchemy.exc import DBAPIError, DisconnectionError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

FLOW_NAME = "weekly-location-performance"
DEPLOYMENT_NAME = "weekly"
SCHEDULE = Cron("0 6 * * 1", timezone="America/Bogota")

DATA_DIR = Path(__file__).resolve().parent.parent
# Entrada de cada corrida, sin datos personales (decisión I4). Fuera de Git.
RAW_DIR = DATA_DIR / "raw" / "telemetry_events"
# Salidas de validación de cada corrida. Fuera de Git.
EVAL_DIR = DATA_DIR / "eval" / "weekly_location_performance"

# Cambia cuando cambian las reglas de data/process: invalida el caché de la transformación.
TRANSFORM_VERSION = "1"
# El envelope que nunca sale de Supabase hacia disco: identifica personas o sesiones.
PERSONAL_TAGS = ("user_id", "session_id", "request_id")


def _utcnow() -> datetime:
    return datetime.now(UTC)


@cache
def get_engine() -> Engine:
    """Un motor por proceso, con la conexión del rol `reporting_pipeline` (bloque o variable)."""
    url, _source = config.load_database_url()
    return repository.create_reporting_engine(url)


def _summarize(error: BaseException) -> str:
    """Tipo y mensaje del error para el log de la corrida, sin cadenas de conexión."""
    message = re.sub(r"postgres(?:ql)?(?:\+\w+)?://\S+", "<conexión>", str(error)).strip()
    return f"{type(error).__name__}: {message}"[:500]


# --- Reintentos -----------------------------------------------------------------------------------

# Solo se reintentan los fallos transitorios de la base (conexión caída, pooler saturado, tiempo de
# espera). Un error de SQL, de permisos o de datos fallaría igual en el reintento: se corta enseguida.
_TRANSIENT_ERRORS = (OperationalError, InterfaceError, DisconnectionError, PoolTimeoutError, ConnectionError, TimeoutError)


def _retry_on_transient_error(task, task_run, state) -> bool:
    error = state.result(raise_on_failure=False)
    if isinstance(error, DBAPIError) and error.connection_invalidated:
        return True
    return isinstance(error, _TRANSIENT_ERRORS)


# --- Caché ----------------------------------------------------------------------------------------

CACHE_TTL = timedelta(hours=1)


def _database_fingerprint() -> str:
    """Distingue bases distintas (Supabase, una copia local, las pruebas) sin guardar la cadena."""
    url, _source = config.load_database_url()
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _locations_cache_key(context: TaskRunContext, parameters: dict[str, Any]) -> str:
    # Clave: la base de la que se lee. El catálogo de locales solo cambia con una migración, así que
    # releerlo en cada corrida es innecesario; vale 1 hora (CACHE_TTL).
    return f"locations-{_database_fingerprint()}"


def _transform_cache_key(context: TaskRunContext, parameters: dict[str, Any]) -> str:
    # Clave: la versión de las reglas, las semanas, los `id` de los eventos extraídos y el catálogo de
    # locales. Los eventos de telemetry_events son inmutables, así que el mismo conjunto de `id` es el
    # mismo contenido: con las mismas entradas, el resultado es idéntico y no hace falta recalcularlo.
    # Un evento nuevo cambia la clave y se recalcula. Vale 1 hora (CACHE_TTL), por debajo de cualquier
    # cadencia razonable entre corridas manuales.
    events: pd.DataFrame = parameters["events"]
    locations: pd.DataFrame = parameters["locations"]
    weeks: list[date] = parameters["weeks"]
    digest = hashlib.sha256()
    digest.update(f"v{TRANSFORM_VERSION}|".encode())
    digest.update(",".join(week.isoformat() for week in sorted(weeks)).encode())
    digest.update(b"|")
    digest.update(",".join(sorted(events["id"].astype(str))).encode())
    digest.update(b"|")
    digest.update(locations.sort_values("id").to_json(orient="records").encode())
    return f"weekly-location-performance-{digest.hexdigest()}"


# --- Tasks ----------------------------------------------------------------------------------------


@task
def resolve_weeks(
    today: date,
    week_from: date | None,
    week_to: date | None,
    lookback_weeks: int,
    max_backfill_weeks: int,
    include_current_week: bool = False,
) -> list[date]:
    """Los lunes que recalcula la corrida (diseño, §3.4).

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
            raise ValueError("week_from y week_to deben ser lunes (week_start de la semana ISO).")
        if week_from > week_to:
            raise ValueError("week_from no puede ser posterior a week_to.")
        if week_to > last_allowed:
            raise ValueError("La semana en curso no está cerrada: no se calcula (usa --include-current-week solo para verificar).")

    weeks = [week_from + timedelta(days=7 * i) for i in range((week_to - week_from).days // 7 + 1)]
    if len(weeks) > max_backfill_weeks:
        raise ValueError(f"El rango tiene {len(weeks)} semanas; el máximo es {max_backfill_weeks}.")
    return weeks


# Dos reintentos cada 10 s: abrir y cerrar el registro son escrituras cortas; si la base sigue sin
# responder tras ~20 s, es una caída y no un parpadeo, y la corrida debe fallar y quedar visible.
@task(retries=2, retry_delay_seconds=10, retry_condition_fn=_retry_on_transient_error)
def open_pipeline_run(
    run_id: UUID | None,
    trigger: str,
    weeks: list[date],
    prefect_flow_run_id: UUID | None,
    stale_run_minutes: int,
) -> UUID:
    """Registra la corrida en `running` en `reporting.pipeline_runs` y cierra las abandonadas."""
    now = _utcnow()
    with get_engine().begin() as conn:
        repository.abandon_stale_runs(conn, now=now, stale_minutes=stale_run_minutes, keep=run_id)
        return repository.start_run(
            conn,
            run_id=run_id,
            trigger=trigger,
            week_from=min(weeks),
            week_to=max(weeks),
            prefect_flow_run_id=prefect_flow_run_id,
            now=now,
        )


# Tres reintentos con espera creciente (10, 30 y 90 s): la extracción es la primera lectura de la
# corrida y la más expuesta a un pooler de Supabase saturado o a un corte breve; 2 minutos cubren esos
# casos sin retrasar demasiado el reporte del lunes.
@task(retries=3, retry_delay_seconds=[10, 30, 90], retry_condition_fn=_retry_on_transient_error)
def extract_business_events(weeks: list[date], environment: str) -> pd.DataFrame:
    """Los eventos de `telemetry_events` (solo lectura) de los cuatro tipos que alimentan un KPI."""
    with get_engine().connect() as conn:
        return repository.fetch_business_events(conn, weeks, environment)


# Mismos reintentos que la otra extracción. Con caché de 1 hora (ver _locations_cache_key).
@task(
    retries=3,
    retry_delay_seconds=[10, 30, 90],
    retry_condition_fn=_retry_on_transient_error,
    cache_key_fn=_locations_cache_key,
    cache_expiration=CACHE_TTL,
    persist_result=True,
)
def extract_locations() -> pd.DataFrame:
    """El catálogo de los 14 locales (`locations`, solo lectura)."""
    with get_engine().connect() as conn:
        return repository.fetch_locations(conn)


# Sin reintentos: no toca servicios externos y es determinista; repetirla daría el mismo error.
# Con caché de 1 hora (ver _transform_cache_key).
@task(cache_key_fn=_transform_cache_key, cache_expiration=CACHE_TTL, persist_result=True)
def transform_weekly_location_performance(
    events: pd.DataFrame, locations: pd.DataFrame, weeks: list[date]
) -> WeeklyPerformanceResult:
    """Las filas de la tabla y los conteos del log, con las reglas de data/process (diseño, §3.3)."""
    return build_weekly_location_performance(events, locations, weeks)


# Dos reintentos (30 y 120 s): la carga es una sola transacción, así que reintentarla es seguro (un
# fallo la deshace entera y el upsert reescribe las mismas filas). Más de dos alargaría la corrida
# por encima de su límite si la base está caída de verdad; la próxima corrida la recupera.
@task(retries=2, retry_delay_seconds=[30, 120], retry_condition_fn=_retry_on_transient_error)
def load_weekly_location_performance(rows: pd.DataFrame) -> int:
    """Upsert de las filas en `reporting.weekly_location_performance`, en una transacción (diseño, §4.1)."""
    with get_engine().begin() as conn:
        return repository.upsert_weekly_location_performance(conn, rows)


# Los mismos dos reintentos que la apertura del registro.
@task(retries=2, retry_delay_seconds=10, retry_condition_fn=_retry_on_transient_error)
def close_pipeline_run(
    run_id: UUID,
    status: str,
    result: WeeklyPerformanceResult | None = None,
    rows_written: int = 0,
    issues: dict[str, int] | None = None,
    failed_task: str | None = None,
    error_message: str | None = None,
) -> None:
    """Cierra la corrida en `completed` o `failed`, con sus conteos y el error si lo hubo."""
    counts: dict[str, Any] = {}
    if result is not None:
        counts = {
            "events_read": result.events_read,
            "events_rejected": result.events_rejected,
            "events_discarded": result.events_discarded,
            "waste_events_without_cost": result.waste_events_without_cost,
        }
    with get_engine().begin() as conn:
        repository.finish_run(
            conn,
            run_id,
            status=status,
            now=_utcnow(),
            issues=issues,
            rows_written=rows_written,
            failed_task=failed_task,
            error_message=error_message,
            **counts,
        )


# Opcional (se invoca con return_state=True): si falla, la corrida sigue y el fallo queda en `issues`.
@task
def save_raw_extract(events: pd.DataFrame, run_id: UUID, weeks: list[date], environment: str) -> str:
    """Guarda la entrada de la corrida en data/raw/telemetry_events/<run_id>.json, sin datos personales."""
    tags = events["tags"].map(lambda value: {k: v for k, v in (value or {}).items() if k not in PERSONAL_TAGS})
    payload = {
        "run_id": str(run_id),
        "extracted_at": _utcnow().isoformat(),
        "environment": environment,
        "weeks": [week.isoformat() for week in weeks],
        "events": pd.DataFrame(
            {
                "id": events["id"].astype(str),
                "timestamp": pd.to_datetime(events["timestamp"], utc=True).map(lambda ts: ts.isoformat()),
                "event_type": events["event_type"],
                "tags": tags,
            }
        ).to_dict(orient="records"),
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{run_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(path)


# Opcional (se invoca con return_state=True): si falla, la corrida sigue y el fallo queda en `issues`.
@task
def export_eval_snapshot(result: WeeklyPerformanceResult, rows_written: int, run_id: UUID, weeks: list[date]) -> str:
    """Escribe en data/eval/weekly_location_performance/<run_id>.json las filas y unas comprobaciones."""
    rows = result.rows
    expected_ratio = (rows["total_waste_cost"] / rows["total_purchase_cost"].where(rows["total_purchase_cost"] > 0)).fillna(0)
    currency_of = {"CO": "COP", "US": "USD"}
    checks = {
        "14_rows_per_week": bool((rows.groupby("week_start").size() == 14).all() and rows["week_start"].nunique() == len(weeks)),
        "waste_ratio_matches_costs": bool(((rows["waste_ratio"] - expected_ratio).abs() <= 0.00005).all()),
        "currency_matches_country": bool((rows["country"].map(currency_of) == rows["currency"]).all()),
        "no_negative_values": bool((rows.select_dtypes("number") >= 0).all().all()),
        "all_rows_written": rows_written == len(rows),
    }
    payload = {
        "run_id": str(run_id),
        "created_at": _utcnow().isoformat(),
        "weeks": [week.isoformat() for week in weeks],
        "checks": checks,
        "counts": {
            "events_read": result.events_read,
            "events_rejected": result.events_rejected,
            "events_discarded": result.events_discarded,
            "waste_events_without_cost": result.waste_events_without_cost,
            "issues": result.issues,
            "rows_written": rows_written,
        },
        "rows": rows.assign(week_start=rows["week_start"].map(date.isoformat)).to_dict(orient="records"),
    }
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    path = EVAL_DIR / f"{run_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


# --- Hooks del flow -------------------------------------------------------------------------------


def _close_run_of_dead_flow(flow, flow_run, state) -> None:
    """El proceso murió (Crashed) o alguien canceló la corrida: la cierra en `failed` (diseño, §5.3)."""
    reason = "cancelled" if state.is_cancelled() else f"crashed: {state.message or ''}".strip()
    try:
        with get_engine().begin() as conn:
            repository.fail_runs_of_flow_run(conn, flow_run.id, now=_utcnow(), error_message=reason[:500])
    except Exception:
        # Si la base tampoco responde, la próxima corrida la marca 'abandoned' (diseño, §4.3).
        logging.getLogger(__name__).exception("No se pudo cerrar en failed la corrida del flow run %s.", flow_run.id)


# --- Flow -----------------------------------------------------------------------------------------


@flow(
    name=FLOW_NAME,
    description="Reporte Semanal de Costo y Merma por Local: de telemetry_events a reporting.weekly_location_performance.",
    timeout_seconds=1800,
    on_crashed=[_close_run_of_dead_flow],
    on_cancellation=[_close_run_of_dead_flow],
)
def weekly_location_performance_flow(
    week_from: date | None = None,
    week_to: date | None = None,
    trigger: str = "scheduled",
    run_id: UUID | None = None,
    environment: str | None = None,
    include_current_week: bool = False,
) -> dict[str, Any]:
    """Extracción → transformación → carga, con el log de la corrida (diseño, §3.2 y §5).

    - Críticas: la extracción, la transformación y la carga. Si una falla, la corrida se cierra en
      `failed` con la task y el error, y el flow termina en Failed.
    - Opcionales (`return_state=True`): `save_raw_extract` y `export_eval_snapshot`. Si fallan, la
      corrida termina en `completed` y el fallo queda en `issues`.
    """
    logger = get_run_logger()
    settings, settings_source = config.load_settings()
    _url, database_source = config.load_database_url()
    environment = environment or settings.environment
    logger.info("Configuración: %s; conexión: %s; entorno de los eventos: %s.", settings_source, database_source, environment)

    weeks = resolve_weeks(
        _utcnow().date(),
        week_from,
        week_to,
        settings.lookback_weeks,
        settings.max_backfill_weeks,
        include_current_week,
    )
    flow_run_id = current_flow_run.id
    run_id = open_pipeline_run(
        run_id, trigger, weeks, UUID(flow_run_id) if flow_run_id else None, settings.stale_run_minutes
    )
    logger.info("Corrida %s: semanas %s a %s.", run_id, weeks[0], weeks[-1])

    # Etapas críticas: un fallo cierra la corrida en `failed` con la task y el error, y se propaga.
    stage = "extract_business_events"
    issues: dict[str, int] = {}
    try:
        events = extract_business_events(weeks, environment)

        raw_state = save_raw_extract(events, run_id, weeks, environment, return_state=True)
        if raw_state.is_failed():
            issues["save_raw_extract_failed"] = 1
            logger.warning("save_raw_extract falló; la corrida sigue: %s", raw_state.message)

        stage = "extract_locations"
        locations = extract_locations()
        stage = "transform_weekly_location_performance"
        result = transform_weekly_location_performance(events, locations, weeks)
    except Exception as error:
        _close_failed(run_id, stage, error)
        raise

    # Carga: el fallo se trata aquí de forma explícita (return_state=True) en lugar de propagarse solo.
    # Cierra la corrida con los conteos de la transformación y el error, y termina el flow en Failed.
    # La transacción ya se deshizo: la tabla conserva los valores de la corrida anterior.
    load_state = load_weekly_location_performance(result.rows, return_state=True)
    if load_state.is_failed():
        error = load_state.result(raise_on_failure=False)
        logger.error("La carga falló; la tabla no cambió: %s", _summarize(error))
        close_pipeline_run(
            run_id,
            "failed",
            result=result,
            issues={**result.issues, **issues},
            failed_task="load_weekly_location_performance",
            error_message=_summarize(error),
        )
        return load_state
    rows_written = load_state.result()

    eval_state = export_eval_snapshot(result, rows_written, run_id, weeks, return_state=True)
    if eval_state.is_failed():
        issues["export_eval_snapshot_failed"] = 1
        logger.warning("export_eval_snapshot falló; la corrida sigue: %s", eval_state.message)

    all_issues = {**result.issues, **issues}
    close_pipeline_run(run_id, "completed", result=result, rows_written=rows_written, issues=all_issues)
    summary = {
        "run_id": str(run_id),
        "status": "completed",
        "week_from": weeks[0].isoformat(),
        "week_to": weeks[-1].isoformat(),
        "environment": environment,
        "events_read": result.events_read,
        "events_rejected": result.events_rejected,
        "events_discarded": result.events_discarded,
        "waste_events_without_cost": result.waste_events_without_cost,
        "issues": all_issues,
        "rows_written": rows_written,
    }
    logger.info("Corrida %s completada: %s", run_id, summary)
    return summary


def _close_failed(run_id: UUID, stage: str, error: BaseException) -> None:
    """Cierra la corrida en `failed` sin tapar el error original si la base tampoco responde."""
    try:
        close_pipeline_run(run_id, "failed", failed_task=stage, error_message=_summarize(error))
    except Exception:  # noqa: BLE001 — la próxima corrida la marcará 'abandoned'
        get_run_logger().exception("No se pudo cerrar la corrida %s en failed.", run_id)


# --- Línea de comandos ----------------------------------------------------------------------------


def serve() -> None:
    """Deployment `weekly-location-performance/weekly`: los lunes a las 06:00 America/Bogota.

    Este mismo proceso ejecuta las corridas programadas y las que pide la API con `run_deployment`,
    una a la vez (límite de concurrencia 1). Necesita un servidor de Prefect (`PREFECT_API_URL`).
    """
    weekly_location_performance_flow.serve(
        name=DEPLOYMENT_NAME,
        schedules=[SCHEDULE],
        global_limit=1,
        tags=["reporting"],
        description="Reporte Semanal de Costo y Merma por Local: lunes 06:00 America/Bogota, 4 últimas semanas cerradas.",
    )


def _parse_week(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"'{value}' no es una fecha YYYY-MM-DD.") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline del Reporte Semanal de Costo y Merma por Local (Prefect).",
    )
    parser.add_argument("--week-from", type=_parse_week, help="Primer lunes del backfill (YYYY-MM-DD).")
    parser.add_argument("--week-to", type=_parse_week, help="Último lunes del backfill (YYYY-MM-DD).")
    parser.add_argument("--environment", help="Entorno de los eventos (por defecto, el de la configuración: production).")
    parser.add_argument(
        "--include-current-week",
        action="store_true",
        help="Incluye la semana en curso, incompleta. Solo para verificar: la corrida del lunes la reescribe.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--serve", action="store_true", help="Sirve el deployment programado de los lunes.")
    group.add_argument("--register-blocks", action="store_true", help="Registra los bloques de Prefect desde el entorno.")
    args = parser.parse_args(argv)

    if args.register_blocks:
        print("Bloques registrados:", ", ".join(config.register_blocks()))
        return 0
    # Sin conexión, un mensaje claro antes de crear una corrida que fallaría al empezar.
    try:
        config.load_database_url()
    except config.ConfigError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if args.serve:
        serve()
        return 0

    summary = weekly_location_performance_flow(
        week_from=args.week_from,
        week_to=args.week_to,
        trigger="manual",
        environment=args.environment,
        include_current_week=args.include_current_week,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
    sys.exit(main())
