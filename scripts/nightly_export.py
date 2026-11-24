"""Script nocturno de telemetría (ticket #DEV-53).

Cada noche, sin intervención manual y fuera de la API:

1. Resuelve `target_date`: `TARGET_DATE` (`YYYY-MM-DD`) o, por defecto, ayer en UTC.
2. Exporta las filas de `telemetry_events` de ese día a
   `data/raw/telemetry_exports/telemetry_YYYY-MM-DD.csv`, solo si el archivo no existe. Es una copia de
   seguridad para auditoría: el pipeline sigue leyendo de la base, no de este archivo.
3. Lanza el pipeline del Hito 6 como subproceso, con este mismo intérprete, sobre las 4 semanas ISO
   cerradas a fecha de `target_date + 1` (decisiones N1 y N2):
   `python data/pipelines/pipeline.py --week-from … --week-to …`.
4. Registra la ejecución en `ops.job_runs` (`pending → processing → completed | failed`) con
   `brasaland_jobs.job_runner.run_job`: el estado `processing` es el lock, la idempotencia es por
   `(nightly_export, target_date)` y ninguna fila se queda en `processing`.

No importa nada de la API ni de FastAPI, ni Prefect: el pipeline corre en su propio proceso.

Uso, desde la raíz del repositorio:

    uv run --project services/jobs python scripts/nightly_export.py
    TARGET_DATE=2026-11-24 uv run --project services/jobs python scripts/nightly_export.py

Configuración en `services/jobs/.env` (plantilla: `.env.example`). Códigos de salida: 0 si terminó,
se omitió por duplicado o se canceló por lock; 1 si falló; 2 si la configuración no es válida.
"""

from __future__ import annotations

import csv
import json
import os
import re
import signal
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from brasaland_jobs.job_runner import (
    DEFAULT_STALE_MINUTES,
    create_jobs_engine,
    error_message_of,
    run_job,
)
from brasaland_jobs.logs import configure_logging
from brasaland_pipelines.runs import DEFAULT_LOOKBACK_WEEKS, compute_weeks
from sqlalchemy import DateTime, Engine, bindparam, text

JOB_NAME = "nightly_export"
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "services" / "jobs" / ".env"
EXPORT_DIR = REPO_ROOT / "data" / "raw" / "telemetry_exports"
PIPELINE_SCRIPT = REPO_ROOT / "data" / "pipelines" / "pipeline.py"
DEFAULT_PIPELINE_TIMEOUT_MINUTES = 90
SIGTERM_EXIT_CODE = 128 + 15

CSV_COLUMNS = ["id", "timestamp", "service", "event_type", "level", "value", "message", "tags"]

# El día completo en UTC: [00:00, 00:00 del día siguiente). Usa el índice de `timestamp` (migración 002).
_EVENTS_OF_DAY_SQL = (
    text(
        """
        SELECT id, "timestamp", service, event_type, level, value, message, tags
        FROM telemetry_events
        WHERE "timestamp" >= :day_start AND "timestamp" < :day_end
        ORDER BY "timestamp", id
        """
    )
    .bindparams(
        bindparam("day_start", type_=DateTime(timezone=True)),
        bindparam("day_end", type_=DateTime(timezone=True)),
    )
    .columns(timestamp=DateTime(timezone=True))
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ConfigError(ValueError):
    """Configuración no válida: el script termina con código 2 sin crear ninguna fila."""


class PipelineFailed(RuntimeError):
    """El subproceso del pipeline terminó con un código distinto de 0."""


# --- Configuración ----------------------------------------------------------------------------------


def utc_today() -> date:
    return datetime.now(UTC).date()


def resolve_target_date(env: Mapping[str, str], today: date) -> date:
    """`TARGET_DATE` si está definida; si no, ayer en UTC. Siempre un día ya terminado."""
    raw = env.get("TARGET_DATE", "").strip()
    if not raw:
        return today - timedelta(days=1)
    if not _ISO_DATE.match(raw):
        raise ConfigError(f"TARGET_DATE debe tener el formato YYYY-MM-DD (recibido: '{raw}').")
    try:
        target = date.fromisoformat(raw)
    except ValueError as error:
        raise ConfigError(f"TARGET_DATE no es una fecha válida: '{raw}'.") from error
    if target >= today:
        # El CSV de un día sin terminar quedaría incompleto, y no se volvería a exportar.
        raise ConfigError(f"TARGET_DATE debe ser un día ya terminado en UTC, anterior a {today.isoformat()}.")
    return target


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    if not raw.isdigit() or int(raw) <= 0:
        raise ConfigError(f"{name} debe ser un número entero de minutos mayor que 0 (recibido: '{raw}').")
    return int(raw)


def load_config(env: Mapping[str, str], today: date) -> dict[str, Any]:
    database_url = env.get("JOBS_DATABASE_URL", "").strip()
    if not database_url:
        raise ConfigError(
            "Falta JOBS_DATABASE_URL (cadena del rol nightly_jobs; ver services/jobs/.env.example)."
        )
    stale_minutes = _positive_int(env, "NIGHTLY_STALE_MINUTES", DEFAULT_STALE_MINUTES)
    timeout_minutes = _positive_int(env, "NIGHTLY_PIPELINE_TIMEOUT_MINUTES", DEFAULT_PIPELINE_TIMEOUT_MINUTES)
    if timeout_minutes >= stale_minutes:
        # Si no, una ejecución legítima podría cerrarse como abandonada mientras el pipeline sigue.
        raise ConfigError(
            f"NIGHTLY_PIPELINE_TIMEOUT_MINUTES ({timeout_minutes}) debe ser menor que "
            f"NIGHTLY_STALE_MINUTES ({stale_minutes})."
        )
    return {
        "database_url": database_url,
        "target_date": resolve_target_date(env, today),
        "stale_minutes": stale_minutes,
        "timeout_minutes": timeout_minutes,
        "pipeline_environment": env.get("NIGHTLY_PIPELINE_ENVIRONMENT", "").strip() or None,
    }


def pipeline_weeks(target_date: date) -> tuple[date, date]:
    """Las 4 semanas ISO cerradas a fecha de `target_date + 1` (N1): la corrida por defecto del pipeline.

    Sin `TARGET_DATE`, `target_date + 1` es hoy, y el resultado es exactamente el del pipeline sin
    rango. Con `TARGET_DATE`, la ventana depende solo de la fecha: nunca incluye una semana sin cerrar.
    """
    weeks = compute_weeks(target_date + timedelta(days=1), None, None, DEFAULT_LOOKBACK_WEEKS)
    return weeks[0], weeks[-1]


# --- Export del CSV -----------------------------------------------------------------------------------


def export_path(target_date: date, export_dir: Path = EXPORT_DIR) -> Path:
    return export_dir / f"telemetry_{target_date.isoformat()}.csv"


def export_csv(engine: Engine, target_date: date, path: Path) -> int | None:
    """Exporta los `telemetry_events` del día a `path`, solo si no existe. Devuelve las filas, o None.

    Escribe en un temporal y lo renombra al final: si el proceso muere a mitad, no queda un CSV
    incompleto que impida exportar el día en la siguiente ejecución.
    """
    if path.exists():
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    day_start = datetime.combine(target_date, time.min, tzinfo=UTC)
    params = {"day_start": day_start, "day_end": day_start + timedelta(days=1)}
    rows = 0
    try:
        with temporary.open("w", newline="", encoding="utf-8") as file, engine.connect() as conn:
            writer = csv.writer(file)
            writer.writerow(CSV_COLUMNS)
            result = conn.execution_options(stream_results=True, yield_per=1000).execute(_EVENTS_OF_DAY_SQL, params)
            for row in result.mappings():
                writer.writerow(format_row(row))
                rows += 1
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return rows


def format_row(row: Mapping[str, Any]) -> list[str]:
    """Una fila del CSV: timestamp en UTC (ISO 8601) y `tags` como JSON compacto con las claves ordenadas."""
    timestamp = row["timestamp"]
    if timestamp.tzinfo is None:  # SQLite (pruebas) guarda la hora UTC sin zona
        timestamp = timestamp.replace(tzinfo=UTC)
    tags = row["tags"]
    if isinstance(tags, str):  # JSONB llega como dict (psycopg2); en SQLite, como texto
        tags = json.loads(tags)
    return [
        str(row["id"]),
        timestamp.astimezone(UTC).isoformat(),
        row["service"],
        row["event_type"],
        row["level"] or "",
        "" if row["value"] is None else str(row["value"]),
        row["message"] or "",
        json.dumps(tags or {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
    ]


# --- Pipeline -----------------------------------------------------------------------------------------


def pipeline_command(week_from: date, week_to: date, environment: str | None) -> list[str]:
    command = [
        sys.executable,
        str(PIPELINE_SCRIPT),
        "--week-from",
        week_from.isoformat(),
        "--week-to",
        week_to.isoformat(),
    ]
    if environment:
        command += ["--environment", environment]
    return command


def run_pipeline(command: list[str], timeout_minutes: int) -> None:
    """Ejecuta el pipeline y espera a que termine. Su salida va al log de este proceso.

    Si no termina en `timeout_minutes`, o si este proceso recibe una interrupción, `subprocess.run`
    mata el subproceso antes de propagar la excepción: no queda un pipeline huérfano.
    """
    result = subprocess.run(command, cwd=REPO_ROOT, timeout=timeout_minutes * 60, check=False)
    if result.returncode != 0:
        raise PipelineFailed(f"El pipeline terminó con código {result.returncode}.")


# --- Ejecución ----------------------------------------------------------------------------------------


def nightly_work(engine: Engine, config: dict[str, Any], log: Any, export_dir: Path = EXPORT_DIR):
    """El trabajo de una ejecución (el `work` de `run_job`): export y pipeline, en ese orden."""
    target_date = config["target_date"]
    extra = {"job": JOB_NAME, "status": "processing"}
    prefix = f"target_date={target_date.isoformat()} | "

    def work() -> None:
        path = export_path(target_date, export_dir)
        rows = export_csv(engine, target_date, path)
        if rows is None:
            log.info(prefix + f"El CSV ya existía, no se exporta de nuevo: {_relative(path)}", extra=extra)
        else:
            log.info(prefix + f"CSV exportado: {_relative(path)} ({rows} filas)", extra=extra)

        week_from, week_to = pipeline_weeks(target_date)
        log.info(prefix + f"Lanzando el pipeline: semanas {week_from.isoformat()} a {week_to.isoformat()}", extra=extra)
        run_pipeline(pipeline_command(week_from, week_to, config["pipeline_environment"]), config["timeout_minutes"])
        log.info(prefix + "El pipeline terminó correctamente", extra=extra)

    return work


def _relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _raise_on_sigterm(signum: int, _frame: Any) -> None:
    # Convierte SIGTERM (docker compose stop, un kill normal) en una excepción: pasa por el finally de
    # run_job y la fila queda en failed. Un SIGKILL no se puede capturar: lo cubre la N11 (abandoned).
    raise SystemExit(SIGTERM_EXIT_CODE)


def main(env: Mapping[str, str] | None = None, *, today: date | None = None, export_dir: Path = EXPORT_DIR) -> int:
    log = configure_logging()
    env = os.environ if env is None else env
    try:
        config = load_config(env, today or utc_today())
    except ConfigError as error:
        log.error(f"Configuración no válida: {error}", extra={"job": JOB_NAME, "status": "failed"})
        return 2

    signal.signal(signal.SIGTERM, _raise_on_sigterm)
    engine = create_jobs_engine(config["database_url"])
    try:
        run_job(
            engine,
            JOB_NAME,
            config["target_date"],
            nightly_work(engine, config, log, export_dir),
            stale_minutes=config["stale_minutes"],
            logger=log,
        )
    except BaseException as error:  # noqa: BLE001 — run_job ya cerró la fila; aquí solo el código de salida
        # La traza ya está en el log si el fallo fue durante la ejecución; esta línea también cubre un
        # fallo antes de crear la fila (p. ej., la base no responde).
        log.error(
            f"target_date={config['target_date'].isoformat()} | Terminó con error: {error_message_of(error)}",
            extra={"job": JOB_NAME, "status": "failed"},
        )
        if isinstance(error, SystemExit) and isinstance(error.code, int):
            return error.code
        return 130 if isinstance(error, KeyboardInterrupt) else 1
    finally:
        engine.dispose()
    # completed, omitida por duplicado o cancelada por lock: las tres son un final normal.
    return 0


if __name__ == "__main__":
    from dotenv import load_dotenv

    # En Windows, la consola y las tuberías usan cp1252 por defecto: los acentos del log saldrían mal.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    load_dotenv(ENV_FILE)
    sys.exit(main())
