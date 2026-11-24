"""Pipeline del "Reporte Semanal de Costo y Merma por Local" (diseño: data/pipelines/PIPELINE_DESIGN.md).

Lee `telemetry_events` y `locations` en solo lectura, calcula por local y semana ISO los cinco KPIs del
briefing y los escribe con upsert en `reporting.weekly_location_performance`. Cada corrida queda en
`reporting.pipeline_runs`. Nunca escribe en `telemetry_events` ni toca el reporte técnico.

Estructura (diseño, §5): el flow principal `weekly_location_performance_flow` coordina tres subflows,
`extract_weekly_location_performance_sources`, `transform_weekly_location_performance` (una task por
KPI) y `load_weekly_location_performance`, y dos opcionales, `archive_weekly_location_performance_extract`
y `export_weekly_location_performance_eval`. Cada subflow se puede ejecutar por separado.

Frecuencia: cada noche, sobre las 4 últimas semanas cerradas. La programa el script nocturno
(`scripts/nightly_export.py`, ticket #DEV-53), que lo lanza por CLI con `--trigger scheduled`; el
deployment de Prefect ya no tiene horario propio (un solo disparador programado).

Ejecución (desde data/pipelines/, con su entorno de uv; o `python data/pipelines/pipeline.py` con ese
entorno activado):

    uv run python pipeline.py                                   # una corrida: las 4 últimas semanas cerradas
    uv run python pipeline.py --week-from 2026-09-07 --week-to 2026-11-16   # backfill por rango
    uv run python pipeline.py --environment development --include-current-week   # verificación en local
    uv run python pipeline.py --register-blocks                 # registra los bloques de Prefect desde .env
    uv run python pipeline.py --serve                           # corridas manuales de la API (necesita PREFECT_API_URL)

La conexión sale del bloque `brasaland-reporting-db` o de `REPORTING_DATABASE_URL` (ver config.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from brasaland_pipelines import config, repository
from brasaland_pipelines.runs import (
    DEPLOYMENT_NAME,
    FLOW_NAME,
    InvalidWeekRange,
    compute_weeks,
)
from brasaland_process import weekly_location_performance as process
from brasaland_process.weekly_location_performance import WeeklyPerformanceResult
from prefect import flow, get_run_logger, task
from prefect.context import TaskRunContext
from prefect.runtime import flow_run as current_flow_run
from prefect.runtime import task_run as prefect_task_run
from sqlalchemy import Engine
from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    InterfaceError,
    OperationalError,
)
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

DATA_DIR = Path(__file__).resolve().parent.parent
# Entrada de cada corrida, sin datos personales (decisión I4). Fuera de Git.
RAW_DIR = DATA_DIR / "raw" / "telemetry_events"
# Salidas de validación de cada corrida. Fuera de Git.
EVAL_DIR = DATA_DIR / "eval" / "weekly_location_performance"

# Cambia cuando cambian las reglas de data/process: invalida el caché de la transformación.
TRANSFORM_VERSION = "2"
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

# psycopg2 también da OperationalError, sin SQLSTATE, cuando la conexión se rechaza por credenciales o
# por un usuario que no existe. No es transitorio, y repetirlo puede hacer que el pooler de Supabase
# bloquee la IP por intentos fallidos: se reconoce por el mensaje del servidor y no se reintenta.
_CREDENTIAL_ERROR_MARKERS = (
    "password authentication failed",
    "tenant/user",  # Supavisor: usuario `rol.<project-ref>` desconocido
    "is not permitted to log in",
    "no pg_hba.conf entry",
)


def _is_credential_error(error: BaseException) -> bool:
    message = str(getattr(error, "orig", None) or error).lower()
    return any(marker in message for marker in _CREDENTIAL_ERROR_MARKERS)


def _retry_on_transient_error(task, task_run, state) -> bool:
    error = state.result(raise_on_failure=False)
    if _is_credential_error(error):
        return False
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


def _facts_cache_key(context: TaskRunContext, parameters: dict[str, Any]) -> str:
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
    return f"weekly-location-facts-{digest.hexdigest()}"


# --- Qué task falló --------------------------------------------------------------------------------

# Los subflows anotan en la excepción la task que falló, para que el flow principal la registre en
# `pipeline_runs.failed_task` aunque el error le llegue a través del subflow.
FAILED_TASK_ATTRIBUTE = "pipeline_failed_task"


@contextmanager
def _failing_task(name: str) -> Iterator[None]:
    try:
        yield
    except Exception as error:
        if not hasattr(error, FAILED_TASK_ATTRIBUTE):
            setattr(error, FAILED_TASK_ATTRIBUTE, name)
        raise


def _failed_task_of(error: BaseException, default: str) -> str:
    return getattr(error, FAILED_TASK_ATTRIBUTE, default)


# --- Tasks de control de la corrida ---------------------------------------------------------------


@task
def resolve_weeks(
    today: date,
    week_from: date | None,
    week_to: date | None,
    lookback_weeks: int,
    max_backfill_weeks: int,
    include_current_week: bool = False,
) -> list[date]:
    """Los lunes que recalcula la corrida (ver `compute_weeks`). Sin reintentos: no toca la base."""
    return compute_weeks(today, week_from, week_to, lookback_weeks, max_backfill_weeks, include_current_week)


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


# Sin reintentos: no toca la base. Pregunta de diseño "silencio vs. ausencia real" (diseño, §12).
@task
def detect_silent_weeks(
    weeks: list[date], telemetry_events_per_week: dict[date, int], business_events: pd.DataFrame
) -> process.SilentWeeks:
    """Semanas sin ninguna telemetría (probable fallo de captura) o sin eventos de negocio."""
    return process.detect_silent_weeks(weeks, telemetry_events_per_week, business_events)


# --- Subflow de extracción ------------------------------------------------------------------------


def _weeks_run_name(task_name: str) -> str:
    """Nombre de la task run con su rango de semanas, para leerlo en la interfaz de Prefect."""
    weeks = prefect_task_run.parameters["weeks"]
    return f"{task_name} {min(weeks)}..{max(weeks)}"


# Tres reintentos con espera creciente (10, 30 y 90 s): la extracción es la primera lectura de la
# corrida y la más expuesta a un pooler de Supabase saturado o a un corte breve; 2 minutos cubren esos
# casos sin retrasar demasiado el reporte del lunes.
@task(
    retries=3,
    retry_delay_seconds=[10, 30, 90],
    retry_condition_fn=_retry_on_transient_error,
    task_run_name=lambda: _weeks_run_name("extract_business_events"),
)
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


# Mismos reintentos que las otras dos lecturas: es la misma base y el mismo tipo de fallo.
@task(
    retries=3,
    retry_delay_seconds=[10, 30, 90],
    retry_condition_fn=_retry_on_transient_error,
    task_run_name=lambda: _weeks_run_name("count_telemetry_events"),
)
def count_telemetry_events(weeks: list[date], environment: str) -> dict[date, int]:
    """Cuántos eventos de telemetría de cualquier tipo llegaron cada semana (señal de silencio, §12)."""
    with get_engine().connect() as conn:
        return repository.count_telemetry_events_per_week(conn, weeks, environment)


@dataclass(frozen=True)
class WeeklyLocationPerformanceSources:
    """Salida del subflow de extracción: lo que leyó la corrida de Supabase."""

    business_events: pd.DataFrame
    locations: pd.DataFrame
    telemetry_events_per_week: dict[date, int]


@flow(
    name="extract_weekly_location_performance_sources",
    description="Extracción (solo lectura): eventos de negocio de telemetry_events, catálogo de locales y volumen de telemetría por semana.",
)
def extract_weekly_location_performance_sources(weeks: list[date], environment: str) -> WeeklyLocationPerformanceSources:
    """Etapa 1 (diseño, §3.1): las fuentes del reporte para las semanas y el entorno pedidos."""
    with _failing_task("extract_business_events"):
        business_events = extract_business_events(weeks, environment)
    with _failing_task("extract_locations"):
        locations = extract_locations()
    with _failing_task("count_telemetry_events"):
        telemetry_events_per_week = count_telemetry_events(weeks, environment)
    return WeeklyLocationPerformanceSources(business_events, locations, telemetry_events_per_week)


# --- Subflow de transformación: una task por KPI del briefing -------------------------------------
#
# Las reglas viven en data/process (funciones puras); estas tasks solo las orquestan. Ninguna se
# reintenta: no tocan servicios externos y son deterministas, así que repetirlas daría el mismo error.


# Con caché de 1 hora (ver _facts_cache_key): es la etapa costosa (expandir `tags`, validar y
# deduplicar); los cálculos de los KPIs que siguen son sumas y conteos sobre sus hechos.
@task(cache_key_fn=_facts_cache_key, cache_expiration=CACHE_TTL, persist_result=True)
def prepare_weekly_location_facts(
    events: pd.DataFrame, locations: pd.DataFrame, weeks: list[date]
) -> process.WeeklyLocationFacts:
    """Los hechos que cuentan (validados, sin duplicados, con su semana) y los conteos del log."""
    return process.prepare_weekly_location_facts(events, locations, weeks)


@task
def compute_total_purchase_cost(facts: pd.DataFrame) -> pd.Series:
    """Costo de compra por local: Σ `quantity × unit_cost` de las entradas, por local y semana."""
    return process.compute_total_purchase_cost(facts)


@task
def compute_total_waste_cost(facts: pd.DataFrame) -> pd.Series:
    """Costo de merma por local: Σ `quantity × unit_cost` de las mermas (0 sin `unit_cost`)."""
    return process.compute_total_waste_cost(facts)


@task
def count_stockout_events(facts: pd.DataFrame) -> pd.Series:
    """Frecuencia de quiebre de stock: `stock_threshold_triggered` por local y semana."""
    return process.count_stockout_events(facts)


@task
def count_price_alert_events(facts: pd.DataFrame) -> pd.Series:
    """Frecuencia de alertas de precio: alertas de subida por local y semana."""
    return process.count_price_alert_events(facts)


@task
def assemble_weekly_location_performance(
    total_purchase_cost: pd.Series,
    total_waste_cost: pd.Series,
    stockout_events_count: pd.Series,
    price_alert_events_count: pd.Series,
    locations: pd.DataFrame,
    weeks: list[date],
) -> pd.DataFrame:
    """Los 14 locales en cada semana, con ceros donde no hubo actividad y su país y moneda."""
    return process.assemble_weekly_location_performance(
        total_purchase_cost, total_waste_cost, stockout_events_count, price_alert_events_count, locations, weeks
    )


@task
def compute_waste_ratio(rows: pd.DataFrame) -> pd.DataFrame:
    """Ratio de merma: `total_waste_cost / total_purchase_cost` de cada fila; 0 sin compras."""
    return process.compute_waste_ratio(rows)


@flow(
    name="transform_weekly_location_performance",
    description="Transformación: los cinco KPIs del briefing por local y semana ISO, una task por KPI.",
)
def transform_weekly_location_performance(
    events: pd.DataFrame, locations: pd.DataFrame, weeks: list[date]
) -> WeeklyPerformanceResult:
    """Etapa 2 (diseño, §3.3): las filas de `reporting.weekly_location_performance` y los conteos del log."""
    with _failing_task("prepare_weekly_location_facts"):
        prepared = prepare_weekly_location_facts(events, locations, weeks)
    facts = prepared.facts
    with _failing_task("compute_total_purchase_cost"):
        total_purchase_cost = compute_total_purchase_cost(facts)
    with _failing_task("compute_total_waste_cost"):
        total_waste_cost = compute_total_waste_cost(facts)
    with _failing_task("count_stockout_events"):
        stockout_events_count = count_stockout_events(facts)
    with _failing_task("count_price_alert_events"):
        price_alert_events_count = count_price_alert_events(facts)
    with _failing_task("assemble_weekly_location_performance"):
        rows = assemble_weekly_location_performance(
            total_purchase_cost, total_waste_cost, stockout_events_count, price_alert_events_count, locations, weeks
        )
    with _failing_task("compute_waste_ratio"):
        rows = compute_waste_ratio(rows)
    return WeeklyPerformanceResult.from_prepared(prepared, rows)


# --- Subflow de carga -----------------------------------------------------------------------------


# Dos reintentos (30 y 120 s): la carga es una sola transacción, así que reintentarla es seguro (un
# fallo la deshace entera y el upsert reescribe las mismas filas). Más de dos alargaría la corrida
# por encima de su límite si la base está caída de verdad; la próxima corrida la recupera.
@task(retries=2, retry_delay_seconds=[30, 120], retry_condition_fn=_retry_on_transient_error)
def upsert_weekly_location_performance(rows: pd.DataFrame) -> int:
    """Upsert de las filas en `reporting.weekly_location_performance`, en una transacción (diseño, §4.1)."""
    with get_engine().begin() as conn:
        return repository.upsert_weekly_location_performance(conn, rows)


@flow(
    name="load_weekly_location_performance",
    description="Carga: upsert idempotente en reporting.weekly_location_performance.",
)
def load_weekly_location_performance(rows: pd.DataFrame) -> int:
    """Etapa 3 (diseño, §3.4): escribe las filas y devuelve cuántas escribió."""
    with _failing_task("upsert_weekly_location_performance"):
        return upsert_weekly_location_performance(rows)


# --- Subflows opcionales (se invocan con return_state=True) ---------------------------------------
#
# Si fallan, la corrida sigue y el fallo queda en `issues`. Sus tasks no se reintentan: escriben un
# archivo local, y un disco lleno o sin permisos no se arregla esperando.


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


@flow(
    name="archive_weekly_location_performance_extract",
    description="Opcional: copia auditable de la extracción de la corrida en data/raw/, sin datos personales.",
)
def archive_weekly_location_performance_extract(
    events: pd.DataFrame, run_id: UUID, weeks: list[date], environment: str
) -> str:
    """Guarda lo que leyó la corrida; devuelve la ruta del archivo."""
    return save_raw_extract(events, run_id, weeks, environment)


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


@flow(
    name="export_weekly_location_performance_eval",
    description="Opcional: filas y comprobaciones de calidad de la corrida en data/eval/.",
)
def export_weekly_location_performance_eval(
    result: WeeklyPerformanceResult, rows_written: int, run_id: UUID, weeks: list[date]
) -> str:
    """Guarda las filas escritas y sus comprobaciones; devuelve la ruta del archivo."""
    return export_eval_snapshot(result, rows_written, run_id, weeks)


# --- Hooks del flow principal ---------------------------------------------------------------------


def _close_run_of_dead_flow(flow, flow_run, state) -> None:
    """El proceso murió (Crashed) o alguien canceló la corrida: la cierra en `failed` (diseño, §5.3)."""
    reason = "cancelled" if state.is_cancelled() else f"crashed: {state.message or ''}".strip()
    try:
        with get_engine().begin() as conn:
            repository.fail_runs_of_flow_run(conn, flow_run.id, now=_utcnow(), error_message=reason[:500])
    except Exception:
        # Si la base tampoco responde, la próxima corrida la marca 'abandoned' (diseño, §4.3).
        logging.getLogger(__name__).exception("No se pudo cerrar en failed la corrida del flow run %s.", flow_run.id)


# --- Flow principal -------------------------------------------------------------------------------


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
    """Coordina los subflows de extracción, transformación y carga, y lleva el log de la corrida.

    No contiene la lógica de ninguna etapa (diseño, §5): resuelve las semanas, abre la corrida, invoca
    los subflows en secuencia y la cierra.

    - Críticos: `extract_weekly_location_performance_sources`, `transform_weekly_location_performance`
      y `load_weekly_location_performance`. Si uno falla, la corrida se cierra en `failed` con la task
      que falló y el error, y el flow termina en Failed. La carga se invoca con `return_state=True` y su
      fallo se trata aquí de forma explícita.
    - Opcionales (`return_state=True`): `archive_weekly_location_performance_extract` y
      `export_weekly_location_performance_eval`. Si fallan, la corrida termina en `completed` y el
      fallo queda en `issues`.
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

    issues: dict[str, int] = {}
    stage = "extract_weekly_location_performance_sources"
    try:
        sources = extract_weekly_location_performance_sources(weeks, environment)

        archive_state = archive_weekly_location_performance_extract(
            sources.business_events, run_id, weeks, environment, return_state=True
        )
        if archive_state.is_failed():
            issues["save_raw_extract_failed"] = 1
            logger.warning("archive_weekly_location_performance_extract falló; la corrida sigue: %s", archive_state.message)

        stage = "detect_silent_weeks"
        silent = detect_silent_weeks(weeks, sources.telemetry_events_per_week, sources.business_events)
        issues.update(silent.issues)
        if silent.without_telemetry:
            logger.warning(
                "Semanas sin ningún evento de telemetría (posible fallo de captura): %s",
                ", ".join(map(str, silent.without_telemetry)),
            )
        if silent.without_business_events:
            logger.warning(
                "Semanas con telemetría pero sin eventos de negocio: %s",
                ", ".join(map(str, silent.without_business_events)),
            )

        stage = "transform_weekly_location_performance"
        result = transform_weekly_location_performance(sources.business_events, sources.locations, weeks)
    except Exception as error:
        _close_failed(run_id, _failed_task_of(error, stage), error)
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
            failed_task=_failed_task_of(error, "load_weekly_location_performance"),
            error_message=_summarize(error),
        )
        return load_state
    rows_written = load_state.result()

    eval_state = export_weekly_location_performance_eval(result, rows_written, run_id, weeks, return_state=True)
    if eval_state.is_failed():
        issues["export_eval_snapshot_failed"] = 1
        logger.warning("export_weekly_location_performance_eval falló; la corrida sigue: %s", eval_state.message)

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


def _close_failed(run_id: UUID, failed_task: str, error: BaseException) -> None:
    """Cierra la corrida en `failed` sin tapar el error original si la base tampoco responde."""
    try:
        close_pipeline_run(run_id, "failed", failed_task=failed_task, error_message=_summarize(error))
    except Exception:  # noqa: BLE001 — la próxima corrida la marcará 'abandoned'
        get_run_logger().exception("No se pudo cerrar la corrida %s en failed.", run_id)


# --- Línea de comandos ----------------------------------------------------------------------------


def serve() -> None:
    """Deployment `weekly-location-performance/weekly`, sin horario: las corridas manuales de la API.

    Este proceso ejecuta las corridas que pide `POST /reporting/pipeline-runs` con `run_deployment`, una
    a la vez (límite de concurrencia 1). Necesita un servidor de Prefect (`PREFECT_API_URL`). La corrida
    programada la lanza cada noche el script nocturno (ticket #DEV-53), no este deployment.
    """
    weekly_location_performance_flow.serve(
        name=DEPLOYMENT_NAME,
        global_limit=1,
        tags=["reporting"],
        description=(
            "Reporte Semanal de Costo y Merma por Local: corridas manuales de la API. "
            "La programada la lanza el script nocturno."
        ),
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
        help="Incluye la semana en curso, incompleta. Solo para verificar: la corrida programada la reescribe.",
    )
    parser.add_argument(
        "--trigger",
        choices=("manual", "scheduled"),
        default="manual",
        help="Origen que queda en pipeline_runs: manual (por defecto) o scheduled (lo pasa el script nocturno).",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--serve", action="store_true", help="Sirve el deployment de las corridas manuales de la API.")
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

    # Un rango inválido, también antes de crear la corrida.
    settings, _source = config.load_settings()
    try:
        compute_weeks(
            _utcnow().date(), args.week_from, args.week_to, settings.lookback_weeks, settings.max_backfill_weeks,
            args.include_current_week,
        )
    except InvalidWeekRange as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    summary = weekly_location_performance_flow(
        week_from=args.week_from,
        week_to=args.week_to,
        trigger=args.trigger,
        environment=args.environment,
        include_current_week=args.include_current_week,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
    sys.exit(main())
