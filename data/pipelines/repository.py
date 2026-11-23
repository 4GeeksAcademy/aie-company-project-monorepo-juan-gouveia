"""Acceso a la base del pipeline del Reporte Semanal de Costo y Merma por Local.

Este paquete es el dueño del esquema `reporting` (decisión P5): aquí está todo su SQL. Lo usan las
tasks de `pipeline.py` y, en solo lectura, los endpoints de `services/reporting/`.

- **Fuente, solo lectura:** `telemetry_events` y `locations`. Nunca se escribe en ellas (además, el rol
  `reporting_pipeline` de la migración 005 no tiene permiso).
- **Destino:** `reporting.weekly_location_performance`, con upsert por `(location_id, week_start)`, y
  el log de corridas `reporting.pipeline_runs`.

El mismo SQL funciona en PostgreSQL (Supabase) y en SQLite (pruebas): los parámetros de fecha van
tipados y el upsert se construye con el dialecto de la conexión.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pandas as pd
from brasaland_process.weekly_location_performance import OUTPUT_COLUMNS, SOURCE_EVENT_TYPES
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Engine,
    Index,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    bindparam,
    create_engine,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

PIPELINE = "weekly_location_performance"
ACTIVE_STATUSES = ("pending", "running")

# --- Tablas de reporting (las de la migración 005) ----------------------------------------------

metadata = MetaData(schema="reporting")

weekly_location_performance = Table(
    "weekly_location_performance",
    metadata,
    Column("id", Uuid, primary_key=True, default=uuid4),
    Column("location_id", Text, nullable=False),
    Column("country", Text, nullable=False),
    Column("week_start", Date, nullable=False),
    Column("total_purchase_cost", Numeric(asdecimal=False), nullable=False, server_default="0"),
    Column("total_waste_cost", Numeric(asdecimal=False), nullable=False, server_default="0"),
    Column("waste_ratio", Numeric(asdecimal=False), nullable=False, server_default="0"),
    Column("stockout_events_count", Integer, nullable=False, server_default="0"),
    Column("price_alert_events_count", Integer, nullable=False, server_default="0"),
    Column("currency", Text, nullable=False),
    Column("computed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("location_id", "week_start"),
)

pipeline_runs = Table(
    "pipeline_runs",
    metadata,
    Column("id", Uuid, primary_key=True, default=uuid4),
    Column("pipeline", Text, nullable=False),
    Column("prefect_flow_run_id", Uuid),
    Column("trigger", Text, nullable=False),
    Column("requested_by", Uuid),
    Column("week_from", Date, nullable=False),
    Column("week_to", Date, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("events_read", Integer, nullable=False, server_default="0"),
    Column("events_rejected", Integer, nullable=False, server_default="0"),
    Column("events_discarded", Integer, nullable=False, server_default="0"),
    Column("waste_events_without_cost", Integer, nullable=False, server_default="0"),
    Column("issues", JSON, nullable=False, default=dict),
    Column("rows_written", Integer, nullable=False, server_default="0"),
    Column("failed_task", Text),
    Column("error_message", Text),
    CheckConstraint("trigger IN ('scheduled', 'manual')", name="pipeline_runs_trigger_check"),
    CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="pipeline_runs_status_check"),
    CheckConstraint("week_from <= week_to", name="pipeline_runs_week_range"),
    Index(
        "uq_pipeline_runs_one_active",
        "pipeline",
        unique=True,
        postgresql_where=text("status IN ('pending', 'running')"),
        sqlite_where=text("status IN ('pending', 'running')"),
    ),
)


class PipelineRunInProgress(RuntimeError):
    """Ya hay una corrida activa del pipeline (índice único parcial de `pipeline_runs`)."""


class PipelineRunNotPending(RuntimeError):
    """La corrida que registró la API ya no está en `pending` (o no existe)."""


def with_psycopg2_driver(url: str) -> str:
    """La cadena tal como la copia Supabase (`postgresql://...`), con el driver psycopg2 explícito.

    SQLAlchemy 2.1 usa por defecto psycopg (v3) para `postgresql://`, que no está instalado: sin
    indicarlo, la conexión falla con ModuleNotFoundError. Lo mismo hace la API (`app.core.database`).
    """
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            return "postgresql+psycopg2://" + url.removeprefix(scheme)
    return url


def create_reporting_engine(url: str) -> Engine:
    """Motor de SQLAlchemy para la cadena del rol `reporting_pipeline`."""
    return create_engine(with_psycopg2_driver(url), pool_pre_ping=True)


# --- Extracción (solo lectura) ------------------------------------------------------------------

_UTC_DATETIME = DateTime(timezone=True)

# Diseño, §3.1: los cuatro tipos de evento de la ventana y del entorno pedido, con los índices de
# `timestamp` y `event_type`. `tags` es JSONB en PostgreSQL y texto JSON en SQLite.
_EVENTS_SQL = (
    text(
        """
        SELECT id, "timestamp", event_type, tags
        FROM telemetry_events
        WHERE event_type IN :event_types
          AND "timestamp" >= :window_start
          AND "timestamp" < :window_end
          AND tags->>'environment' = :environment
        ORDER BY "timestamp", id
        """
    )
    .bindparams(
        bindparam("event_types", expanding=True),
        bindparam("window_start", type_=_UTC_DATETIME),
        bindparam("window_end", type_=_UTC_DATETIME),
    )
    .columns(tags=JSON)
)

_LOCATIONS_SQL = text("SELECT id, code, name, country, currency FROM locations ORDER BY id")


def week_window(weeks: list[date]) -> tuple[datetime, datetime]:
    """Del lunes 00:00 UTC de la primera semana al lunes siguiente a la última (fin exclusivo)."""
    start = datetime.combine(min(weeks), datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(max(weeks) + timedelta(days=7), datetime.min.time(), tzinfo=UTC)
    return start, end


def fetch_business_events(conn: Connection, weeks: list[date], environment: str) -> pd.DataFrame:
    """Eventos de los cuatro tipos que alimentan un KPI, en las semanas de la corrida."""
    window_start, window_end = week_window(weeks)
    result = conn.execute(
        _EVENTS_SQL,
        {
            "event_types": list(SOURCE_EVENT_TYPES),
            "window_start": window_start,
            "window_end": window_end,
            "environment": environment,
        },
    )
    return pd.DataFrame(result.mappings().all(), columns=["id", "timestamp", "event_type", "tags"])


def fetch_locations(conn: Connection) -> pd.DataFrame:
    """El catálogo de los 14 locales (migración 004)."""
    result = conn.execute(_LOCATIONS_SQL)
    return pd.DataFrame(result.mappings().all(), columns=["id", "code", "name", "country", "currency"])


# --- Carga (upsert) -----------------------------------------------------------------------------

_UPDATED_COLUMNS = [c for c in OUTPUT_COLUMNS if c not in ("location_id", "week_start")]


def upsert_weekly_location_performance(conn: Connection, rows: pd.DataFrame) -> int:
    """Escribe las filas con un único `INSERT … ON CONFLICT (location_id, week_start) DO UPDATE`.

    Sustituye los valores de la semana, nunca los suma: correr dos veces sobre los mismos datos deja la
    tabla igual (diseño, §3.4 y §4.1). Quien llama abre la transacción: si falla, no queda nada a medias.
    """
    records = rows[OUTPUT_COLUMNS].to_dict(orient="records")
    if not records:
        return 0
    dialect_insert = postgresql.insert if conn.dialect.name == "postgresql" else sqlite.insert
    statement = dialect_insert(weekly_location_performance).values(records)
    statement = statement.on_conflict_do_update(
        index_elements=["location_id", "week_start"],
        set_={**{column: statement.excluded[column] for column in _UPDATED_COLUMNS}, "computed_at": func.now()},
    )
    conn.execute(statement)
    return len(records)


# --- Log de corridas ----------------------------------------------------------------------------


def abandon_stale_runs(conn: Connection, *, now: datetime, stale_minutes: int, keep: UUID | None = None) -> int:
    """Marca como `failed` ('abandoned') las corridas activas más antiguas que `stale_minutes`.

    Una corrida cuyo proceso murió sin cerrar su registro bloquearía el índice de corrida activa.
    """
    condition = (
        (pipeline_runs.c.pipeline == PIPELINE)
        & pipeline_runs.c.status.in_(ACTIVE_STATUSES)
        & (pipeline_runs.c.created_at < now - timedelta(minutes=stale_minutes))
    )
    if keep is not None:
        condition &= pipeline_runs.c.id != keep
    result = conn.execute(
        update(pipeline_runs).where(condition).values(status="failed", finished_at=now, error_message="abandoned")
    )
    return result.rowcount


def create_pending_run(
    conn: Connection, *, week_from: date, week_to: date, requested_by: UUID | None, now: datetime
) -> UUID:
    """Registra una corrida manual en `pending` antes de pedírsela a Prefect (`POST /reporting/pipeline-runs`)."""
    run_id = uuid4()
    try:
        conn.execute(
            insert(pipeline_runs).values(
                id=run_id,
                pipeline=PIPELINE,
                trigger="manual",
                requested_by=requested_by,
                week_from=week_from,
                week_to=week_to,
                status="pending",
                created_at=now,
                issues={},
            )
        )
    except IntegrityError as error:
        raise PipelineRunInProgress("Ya hay una corrida activa del pipeline.") from error
    return run_id


def start_run(
    conn: Connection,
    *,
    run_id: UUID | None,
    trigger: str,
    week_from: date,
    week_to: date,
    prefect_flow_run_id: UUID | None,
    now: datetime,
) -> UUID:
    """Pone la corrida en `running`.

    Con `run_id` (corrida manual que registró la API), la pasa de `pending` a `running`; sin él
    (corrida programada o desde la línea de comandos), la crea ya en `running`.
    """
    if run_id is not None:
        result = conn.execute(
            update(pipeline_runs)
            .where((pipeline_runs.c.id == run_id) & (pipeline_runs.c.status == "pending"))
            .values(status="running", started_at=now, prefect_flow_run_id=prefect_flow_run_id)
        )
        if result.rowcount != 1:
            raise PipelineRunNotPending(f"La corrida {run_id} no existe o ya no está en pending.")
        return run_id

    new_id = uuid4()
    try:
        conn.execute(
            insert(pipeline_runs).values(
                id=new_id,
                pipeline=PIPELINE,
                prefect_flow_run_id=prefect_flow_run_id,
                trigger=trigger,
                week_from=week_from,
                week_to=week_to,
                status="running",
                created_at=now,
                started_at=now,
                issues={},
            )
        )
    except IntegrityError as error:
        raise PipelineRunInProgress("Ya hay una corrida activa del pipeline.") from error
    return new_id


def finish_run(
    conn: Connection,
    run_id: UUID,
    *,
    status: str,
    now: datetime,
    events_read: int = 0,
    events_rejected: int = 0,
    events_discarded: int = 0,
    waste_events_without_cost: int = 0,
    issues: dict[str, int] | None = None,
    rows_written: int = 0,
    failed_task: str | None = None,
    error_message: str | None = None,
) -> None:
    """Cierra la corrida en `completed` o `failed`, con los conteos y el error."""
    conn.execute(
        update(pipeline_runs)
        .where(pipeline_runs.c.id == run_id)
        .values(
            status=status,
            finished_at=now,
            events_read=events_read,
            events_rejected=events_rejected,
            events_discarded=events_discarded,
            waste_events_without_cost=waste_events_without_cost,
            issues=issues or {},
            rows_written=rows_written,
            failed_task=failed_task,
            error_message=error_message,
        )
    )


def fail_runs_of_flow_run(conn: Connection, prefect_flow_run_id: UUID, *, now: datetime, error_message: str) -> int:
    """Cierra en `failed` la corrida activa de un flow run de Prefect que se cayó o se canceló."""
    result = conn.execute(
        update(pipeline_runs)
        .where((pipeline_runs.c.prefect_flow_run_id == prefect_flow_run_id) & pipeline_runs.c.status.in_(ACTIVE_STATUSES))
        .values(status="failed", finished_at=now, error_message=error_message)
    )
    return result.rowcount


def set_prefect_flow_run_id(conn: Connection, run_id: UUID, prefect_flow_run_id: UUID) -> None:
    """Enlaza la corrida manual con el flow run que Prefect creó para ella."""
    conn.execute(update(pipeline_runs).where(pipeline_runs.c.id == run_id).values(prefect_flow_run_id=prefect_flow_run_id))


# --- Lecturas para los endpoints de services/reporting ------------------------------------------


def read_pipeline_run(conn: Connection, run_id: UUID) -> dict[str, Any] | None:
    """Una corrida por su id."""
    row = conn.execute(select(pipeline_runs).where(pipeline_runs.c.id == run_id)).mappings().first()
    return dict(row) if row else None


def read_latest_pipeline_run(conn: Connection, pipeline: str = PIPELINE) -> dict[str, Any] | None:
    """La última corrida del pipeline por `created_at` (`GET /reporting/pipeline-runs/latest`)."""
    row = (
        conn.execute(
            select(pipeline_runs)
            .where(pipeline_runs.c.pipeline == pipeline)
            .order_by(pipeline_runs.c.created_at.desc())
            .limit(1)
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


# Solo para el nombre del local en la respuesta de KPIs (decisión P2). Es la tabla de la migración 004,
# en el esquema público.
_locations = Table("locations", MetaData(), Column("code", Text), Column("name", Text), Column("id", Integer))


def read_weekly_location_performance(conn: Connection, week_start: date | None = None) -> tuple[date, list[dict[str, Any]]] | None:
    """Los locales de una semana (`GET /reporting/weekly-location-performance`).

    Sin `week_start`, la semana calculada más reciente. Devuelve `(week_start, filas)` con
    `location_name` cruzado con `locations`, ordenadas por país y por el id del local; `None` si esa
    semana (o ninguna) está calculada.
    """
    table = weekly_location_performance
    if week_start is None:
        week_start = conn.execute(select(func.max(table.c.week_start))).scalar_one_or_none()
        if week_start is None:
            return None
    rows = (
        conn.execute(
            select(
                table.c.location_id,
                _locations.c.name.label("location_name"),
                table.c.country,
                table.c.total_purchase_cost,
                table.c.total_waste_cost,
                table.c.waste_ratio,
                table.c.stockout_events_count,
                table.c.price_alert_events_count,
                table.c.currency,
            )
            .select_from(table.outerjoin(_locations, _locations.c.code == table.c.location_id))
            .where(table.c.week_start == week_start)
            .order_by(table.c.country, _locations.c.id, table.c.location_id)
        )
        .mappings()
        .all()
    )
    if not rows:
        return None
    return week_start, [dict(row) for row in rows]
