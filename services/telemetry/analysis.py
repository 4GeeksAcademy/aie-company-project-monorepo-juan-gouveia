"""Pipeline de análisis de la telemetría: métricas técnicas sobre `telemetry_events`.

Plan de telemetría, sección 16. Es un reporte técnico para el equipo de ingeniería (volumen, errores,
latencia y fallos de autenticación), no un reporte de negocio.

Cada métrica es una función independiente y sin efectos secundarios: solo lee la base, así que dos
llamadas con los mismos parámetros devuelven lo mismo. Todas siguen el mismo orden:

    cargar (SQL) → refinar (Pandas) → convertir tipos → agrupar → agregar → servir

- **Cargar.** Solo las filas que la métrica necesita: la ventana `[start, end)` (inicio inclusivo, fin
  exclusivo, en UTC) y, si aplica, los `event_type` de la métrica, siempre en SQL. La ventana la decide
  quien llama (el endpoint); estas funciones no aplican ninguna por defecto.
- **Refinar.** Extraer de `tags` las dimensiones de la métrica y descartar las filas en las que faltan.
- **Convertir tipos.** `timestamp` llega como texto (SQLite) o como `datetime` (PostgreSQL), según el
  driver: siempre se convierte con `pd.to_datetime(..., utc=True)` antes de agrupar por día. Agrupar
  por un texto que parece una fecha daría grupos incorrectos sin ningún error.
- **Agrupar y agregar.** `groupby` por día UTC y por la dimensión de la métrica, con `.agg()`,
  `.size()`, `.sum()` o `.mean()`. Sin bucles.
- **Servir.** Una lista de dicts con tipos nativos de Python, serializable a JSON tal cual: fechas
  `YYYY-MM-DD` y tasas como fracción de 0 a 1 con 4 decimales.
"""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import JSON, DateTime, bindparam, text
from sqlalchemy.engine import Connection
from sqlalchemy.sql.elements import TextClause

Records = list[dict[str, Any]]

LEVELS = ["info", "warn", "error"]
FAILURE_LEVELS = ["warn", "error"]
LATENCY_EVENT = "api_latency_recorded"
LOGIN_FAILED = "login_failed"
LOGIN_SUCCEEDED = "login_succeeded"
RATE_DECIMALS = 4
MS_DECIMALS = 1

# Parámetros de la ventana con su tipo: cada dialecto los escribe como compara sus timestamps.
_UTC_DATETIME = DateTime(timezone=True)


def _query(sql: str, *, json_tags: bool = False, expanding: str | None = None) -> TextClause:
    """Consulta con los límites `:start` y `:end` tipados. `timestamp` se deja tal como lo da el driver."""
    params = [bindparam("start", type_=_UTC_DATETIME), bindparam("end", type_=_UTC_DATETIME)]
    if expanding:
        params.append(bindparam(expanding, expanding=True))
    query = text(sql).bindparams(*params)
    # tags es JSONB en PostgreSQL (llega como dict) y texto JSON en SQLite: JSON lo decodifica si hace falta.
    return query.columns(tags=JSON) if json_tags else query


# --- Consultas (cargar) ----------------------------------------------------------------------------------

EVENTS_SQL = _query(
    """
    SELECT timestamp, event_type, level
    FROM telemetry_events
    WHERE timestamp >= :start AND timestamp < :end
    """
)

LATENCY_SQL = _query(
    """
    SELECT timestamp, tags
    FROM telemetry_events
    WHERE timestamp >= :start AND timestamp < :end
      AND event_type = :event_type
    """,
    json_tags=True,
)

LOGIN_SQL = _query(
    """
    SELECT timestamp, event_type
    FROM telemetry_events
    WHERE timestamp >= :start AND timestamp < :end
      AND event_type IN :event_types
    """,
    expanding="event_types",
)


def _load(connection: Connection, query: TextClause, start: datetime, end: datetime, **params: Any) -> pd.DataFrame:
    return pd.read_sql(query, connection, params={"start": start, "end": end, **params})


def _to_utc_day(frame: pd.DataFrame) -> pd.DataFrame:
    """Convierte `timestamp` a datetime UTC y añade `date`, el día UTC del evento."""
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, format="ISO8601")
    frame["date"] = frame["timestamp"].dt.date
    return frame


def _serve(frame: pd.DataFrame) -> Records:
    """Lista de dicts con la fecha en ISO, lista para JSON."""
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    return frame.to_dict(orient="records")


# --- Métricas --------------------------------------------------------------------------------------------


def events_per_day(connection: Connection, start: datetime, end: datetime) -> Records:
    """¿Cuánto volumen tiene el sistema cada día y qué parte es aviso o error?

    Una fila por día de la ventana, también los días sin eventos (con ceros), para que un hueco en la
    captura se vea como tal: `{date, total, info, warn, error}`.
    """
    # 1. Cargar: todos los eventos de la ventana, solo las columnas que se usan.
    events = _load(connection, EVENTS_SQL, start, end)
    # 2. Refinar: el nivel es obligatorio en la tabla, pero una fila sin él no puede clasificarse.
    events = events.dropna(subset=["level"])
    # 3. Convertir tipos.
    events = _to_utc_day(events)
    # 4. Agrupar por día y nivel, y 5. agregar contando eventos.
    counts = events.groupby(["date", "level"]).size().unstack("level", fill_value=0)
    days = pd.date_range(start.date(), (end - timedelta(microseconds=1)).date(), freq="D").date
    counts = counts.reindex(index=pd.Index(days, name="date"), columns=LEVELS, fill_value=0)
    counts["total"] = counts[LEVELS].sum(axis=1)
    # 6. Servir.
    return _serve(counts.reset_index()[["date", "total", *LEVELS]])


def error_rate_by_type(connection: Connection, start: datetime, end: datetime) -> Records:
    """¿Qué tipos de fallo dominan cada día y qué peso tienen sobre el volumen?

    Una fila por día y tipo de evento de nivel `warn` o `error`: `{date, event_type, level, count, rate}`,
    donde `rate` es la fracción de los eventos de ese día que son de ese tipo. El denominador son todos
    los eventos del día, así que la consulta carga todos los tipos de una vez.
    """
    # 1. Cargar: todos los eventos de la ventana (el total del día es el denominador de la tasa).
    events = _load(connection, EVENTS_SQL, start, end)
    # 2. Refinar: sin tipo o sin nivel, un evento no se puede atribuir.
    events = events.dropna(subset=["event_type", "level"])
    # 3. Convertir tipos.
    events = _to_utc_day(events)
    # 4. Agrupar: el volumen total de cada día y los fallos por día, tipo y nivel.
    day_totals = events.groupby("date").size().rename("day_total")
    failures = events[events["level"].isin(FAILURE_LEVELS)]
    by_type = failures.groupby(["date", "event_type", "level"]).size().rename("count").reset_index()
    # 5. Agregar: la tasa de cada tipo sobre el total de su día.
    by_type = by_type.join(day_totals, on="date")
    by_type["rate"] = (by_type["count"] / by_type["day_total"]).round(RATE_DECIMALS)
    by_type = by_type.sort_values(["date", "count", "event_type"], ascending=[True, False, True])
    # 6. Servir.
    return _serve(by_type[["date", "event_type", "level", "count", "rate"]].reset_index(drop=True))


def api_latency_by_route(connection: Connection, start: datetime, end: datetime) -> Records:
    """¿Qué rutas de la API responden lento y cuánto?

    Una fila por día, método y ruta: `{date, method, route, samples, avg_ms, max_ms}`. Las latencias
    son un muestreo (se guardan siempre las lentas y las de error, y una de cada `1/sample_rate` del
    resto), así que la media se pondera por `1/sample_rate`: sin ponderar, las lentas pesarían de más.
    `samples` cuenta eventos y `max_ms` es el máximo observado, sin ponderar.
    """
    # 1. Cargar: solo los eventos de latencia de la ventana.
    latencies = _load(connection, LATENCY_SQL, start, end, event_type=LATENCY_EVENT)
    # 2. Refinar: extraer las dimensiones de tags y descartar las filas sin ruta o sin duración.
    tags = latencies["tags"]
    latencies["method"] = tags.str.get("method")
    latencies["route"] = tags.str.get("route")
    latencies["duration_ms"] = pd.to_numeric(tags.str.get("duration_ms"), errors="coerce")
    sample_rate = pd.to_numeric(tags.str.get("sample_rate"), errors="coerce")
    # Un sample_rate ausente o fuera de (0, 1] cuenta como evento no muestreado (peso 1).
    latencies["weight"] = 1 / sample_rate.where((sample_rate > 0) & (sample_rate <= 1), 1.0)
    latencies = latencies.dropna(subset=["method", "route", "duration_ms"])
    latencies["weighted_ms"] = latencies["duration_ms"] * latencies["weight"]
    # 3. Convertir tipos.
    latencies = _to_utc_day(latencies)
    # 4. Agrupar por día, método y ruta, y 5. agregar.
    by_route = latencies.groupby(["date", "method", "route"]).agg(
        samples=("duration_ms", "count"),
        weighted_ms=("weighted_ms", "sum"),
        weight=("weight", "sum"),
        max_ms=("duration_ms", "max"),
    )
    by_route["avg_ms"] = (by_route["weighted_ms"] / by_route["weight"]).round(MS_DECIMALS)
    by_route["max_ms"] = by_route["max_ms"].round(MS_DECIMALS)
    by_route = by_route.reset_index().sort_values(["date", "avg_ms", "route"], ascending=[True, False, True])
    # 6. Servir.
    return _serve(by_route[["date", "method", "route", "samples", "avg_ms", "max_ms"]].reset_index(drop=True))


def auth_failure_rate(connection: Connection, start: datetime, end: datetime) -> Records:
    """¿Qué proporción de los intentos de login falla cada día?

    Una fila por día con intentos: `{date, attempts, failed, failure_rate}`, con
    `failure_rate = login_failed / (login_failed + login_succeeded)`. Los dos tipos se cargan en una
    sola consulta con `IN`, y la razón se calcula en Pandas.
    """
    # 1. Cargar: los dos tipos de evento del login en una sola consulta.
    logins = _load(connection, LOGIN_SQL, start, end, event_types=[LOGIN_FAILED, LOGIN_SUCCEEDED])
    # 2. Refinar: el flag derivado de cada intento.
    logins = logins.dropna(subset=["event_type"])
    logins["is_failed"] = logins["event_type"].eq(LOGIN_FAILED).astype(int)
    # 3. Convertir tipos.
    logins = _to_utc_day(logins)
    # 4. Agrupar por día y 5. agregar.
    by_day = logins.groupby("date").agg(attempts=("is_failed", "count"), failed=("is_failed", "sum"))
    by_day["failure_rate"] = (by_day["failed"] / by_day["attempts"]).round(RATE_DECIMALS)
    # 6. Servir.
    return _serve(by_day.reset_index()[["date", "attempts", "failed", "failure_rate"]])
