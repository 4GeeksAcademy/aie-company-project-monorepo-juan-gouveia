"""Transformación del "Reporte Semanal de Costo y Merma por Local" (diseño, §3.3).

Funciones puras de Pandas, sin acceso a la base ni bucles sobre filas: reciben los eventos que extrajo
el pipeline de `telemetry_events`, el catálogo `locations` y las semanas de la corrida, y devuelven las
filas de `reporting.weekly_location_performance` y los conteos que van al log de la corrida
(`reporting.pipeline_runs`). La orquestación y el acceso a la base viven en `data/pipelines/`.

Orden: refinar → validar contra el local → deduplicar el hecho → filtrar las alertas de bajada →
semana ISO (UTC) → importes → agregar por local y semana → completar los 14 locales → ratio.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

# Los cuatro eventos obligatorios que alimentan un KPI (briefing del pipeline, §3).
INBOUND = "inbound_order_created"
WASTE = "stock_waste_registered"
STOCKOUT = "stock_threshold_triggered"
PRICE_ALERT = "ingredient_price_variance_detected"
SOURCE_EVENT_TYPES = (INBOUND, WASTE, STOCKOUT, PRICE_ALERT)

# Motivos con los que un evento se excluye; su conteo va a `pipeline_runs.issues` (diseño, §4.4).
# Rechazados (datos inválidos):
UNKNOWN_LOCATION = "unknown_location"
COUNTRY_MISMATCH = "country_mismatch"
CURRENCY_MISMATCH = "currency_mismatch"
INVALID_PAYLOAD = "invalid_payload"
REJECTION_REASONS = (UNKNOWN_LOCATION, COUNTRY_MISMATCH, CURRENCY_MISMATCH, INVALID_PAYLOAD)
# Descartados (por regla):
DUPLICATE_FACT = "duplicate_fact"
PRICE_DECREASE = "price_decrease"
OUTSIDE_WINDOW = "outside_window"

# Columnas de `reporting.weekly_location_performance` que calcula el pipeline (las del briefing, §5,
# sin `id` ni `computed_at`, que pone la base).
OUTPUT_COLUMNS = [
    "location_id",
    "country",
    "week_start",
    "total_purchase_cost",
    "total_waste_cost",
    "waste_ratio",
    "stockout_events_count",
    "price_alert_events_count",
    "currency",
]

# Propiedades de `tags` que usa la transformación (catálogo de telemetría 1.3.0). Nunca `user_id`,
# `session_id` ni `request_id`.
_TEXT_TAGS = ["country", "currency", "schema_version"]
_NUMERIC_TAGS = ["location_id", "order_id", "trigger_order_id", "quantity", "unit_cost", "variance_pct"]
BUSINESS_TAGS = _TEXT_TAGS + _NUMERIC_TAGS


@dataclass(frozen=True)
class WeeklyPerformanceResult:
    """Salida de la transformación: las filas de la tabla y los conteos del log de la corrida.

    Cumple `events_read = eventos usados + events_rejected + events_discarded`.
    """

    rows: pd.DataFrame
    events_read: int
    events_rejected: int
    events_discarded: int
    waste_events_without_cost: int
    issues: dict[str, int] = field(default_factory=dict)


def _as_dict(value: Any) -> dict:
    """`tags` llega como dict (jsonb con psycopg2) o como texto JSON (SQLite en las pruebas)."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        return json.loads(value)
    return {}


def week_start_of(timestamps: pd.Series) -> pd.Series:
    """Lunes de la semana ISO de cada instante, en UTC (briefing, §4), como `datetime.date`."""
    utc = pd.to_datetime(timestamps, utc=True)
    return (utc.dt.normalize() - pd.to_timedelta(utc.dt.day_of_week, unit="D")).dt.date


def refine_events(events: pd.DataFrame) -> pd.DataFrame:
    """Paso 1: una columna por cada propiedad de negocio de `tags`, con su tipo.

    `events` tiene las columnas de la extracción: `id`, `timestamp`, `event_type` y `tags`.
    """
    flat = pd.json_normalize(events["tags"].map(_as_dict).tolist()).reindex(columns=BUSINESS_TAGS)
    flat.index = events.index
    flat[_NUMERIC_TAGS] = flat[_NUMERIC_TAGS].apply(pd.to_numeric, errors="coerce")
    refined = pd.DataFrame(
        {
            "event_id": events["id"].astype(str),
            "timestamp": pd.to_datetime(events["timestamp"], utc=True, format="ISO8601"),
            "event_type": events["event_type"].astype(str),
        },
        index=events.index,
    )
    return pd.concat([refined, flat], axis=1)


def validate_events(refined: pd.DataFrame, locations: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Paso 2: descarta los eventos que no se pueden atribuir a un local con su país y su moneda.

    Motivos, en este orden: local fuera del catálogo, país o moneda distintos de los del local, o un
    dato imprescindible ausente o inválido (`invalid_payload`). Devuelve los válidos y el conteo de
    rechazados por motivo.
    """
    catalog = locations.set_index("id")
    location = refined["location_id"]
    expected_country = location.map(catalog["country"])
    expected_currency = location.map(catalog["currency"])

    kind = refined["event_type"]
    has_order = refined["order_id"].notna()
    positive_quantity = refined["quantity"] > 0
    unit_cost = refined["unit_cost"]
    invalid_payload = (
        ((kind == INBOUND) & ~(has_order & positive_quantity & (unit_cost > 0)))
        # En la merma, `unit_cost` es opcional (1.1.0), pero si llega debe ser positivo.
        | ((kind == WASTE) & ~(has_order & positive_quantity & (unit_cost.isna() | (unit_cost > 0))))
        | ((kind == STOCKOUT) & refined["trigger_order_id"].isna())
        | ((kind == PRICE_ALERT) & ~(has_order & refined["variance_pct"].notna()))
        | ~kind.isin(SOURCE_EVENT_TYPES)
    )

    reason = pd.Series(
        np.select(
            [
                ~location.isin(catalog.index),
                refined["country"] != expected_country,
                refined["currency"] != expected_currency,
                invalid_payload,
            ],
            list(REJECTION_REASONS),
            default="",
        ),
        index=refined.index,
    )
    rejected = reason[reason != ""]
    valid = refined[reason == ""].astype({"location_id": "int64"})
    return valid, {str(k): int(v) for k, v in rejected.value_counts().items()}


def deduplicate_facts(valid: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Paso 3: un mismo hecho emitido dos veces con otro `eventId` cuenta una vez.

    La clave es `(event_type, order_id)`, o `trigger_order_id` en los quiebres; se conserva el evento
    más antiguo (y, a igual `timestamp`, el de menor id, para que el resultado sea siempre el mismo).
    """
    fact_key = valid["order_id"].where(valid["event_type"] != STOCKOUT, valid["trigger_order_id"])
    ordered = valid.assign(fact_key=fact_key).sort_values(["timestamp", "event_id"], kind="stable")
    duplicated = ordered.duplicated(subset=["event_type", "fact_key"], keep="first")
    return ordered[~duplicated].drop(columns="fact_key"), int(duplicated.sum())


def keep_price_increases(facts: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Paso 4: de las alertas de precio solo cuentan las subidas (`variance_pct > 0`, decisión P3)."""
    decrease = (facts["event_type"] == PRICE_ALERT) & ~(facts["variance_pct"] > 0)
    return facts[~decrease], int(decrease.sum())


def aggregate_weekly(facts: pd.DataFrame) -> pd.DataFrame:
    """Pasos 6 y 7: importes por evento y suma por local y semana.

    Compra y merma: `quantity × unit_cost`, en la moneda del local; una merma sin `unit_cost` cuenta 0.
    Quiebres y alertas: número de eventos.
    """
    kind = facts["event_type"]
    cost = facts["quantity"] * facts["unit_cost"].fillna(0)
    measures = facts.assign(
        purchase_cost=cost.where(kind == INBOUND, 0.0),
        waste_cost=cost.where(kind == WASTE, 0.0),
        stockouts=(kind == STOCKOUT).astype("int64"),
        price_alerts=(kind == PRICE_ALERT).astype("int64"),
    )
    return measures.groupby(["location_id", "week_start"]).agg(
        total_purchase_cost=("purchase_cost", "sum"),
        total_waste_cost=("waste_cost", "sum"),
        stockout_events_count=("stockouts", "sum"),
        price_alert_events_count=("price_alerts", "sum"),
    )


def complete_and_finalize(weekly: pd.DataFrame, locations: pd.DataFrame, weeks: list[date]) -> pd.DataFrame:
    """Pasos 8 a 10: los 14 locales en cada semana (con ceros), el ratio y las dimensiones del local.

    `waste_ratio = total_waste_cost / total_purchase_cost`, con 4 decimales; 0 si no hubo compras.
    Los importes, con 2 decimales en la moneda del local, sin convertir. `location_id` pasa a ser el
    `code` del local (decisión P2).
    """
    grid = pd.MultiIndex.from_product([sorted(locations["id"]), sorted(weeks)], names=["location_id", "week_start"])
    rows = weekly.reindex(grid, fill_value=0).reset_index()

    purchase = rows["total_purchase_cost"].astype("float64")
    waste = rows["total_waste_cost"].astype("float64")
    catalog = locations.set_index("id")
    rows = rows.assign(
        total_purchase_cost=purchase.round(2),
        total_waste_cost=waste.round(2),
        waste_ratio=(waste / purchase.where(purchase > 0)).fillna(0.0).round(4),
        stockout_events_count=rows["stockout_events_count"].astype("int64"),
        price_alert_events_count=rows["price_alert_events_count"].astype("int64"),
        country=rows["location_id"].map(catalog["country"]),
        currency=rows["location_id"].map(catalog["currency"]),
        location_id=rows["location_id"].map(catalog["code"]),
    )
    return rows[OUTPUT_COLUMNS].reset_index(drop=True)


def build_weekly_location_performance(
    events: pd.DataFrame, locations: pd.DataFrame, weeks: list[date]
) -> WeeklyPerformanceResult:
    """Transforma los eventos de una corrida en las filas de `reporting.weekly_location_performance`.

    - `events`: la extracción (`id`, `timestamp`, `event_type`, `tags`) de los cuatro tipos de evento.
    - `locations`: el catálogo (`id`, `code`, `country`, `currency`).
    - `weeks`: los lunes de las semanas de la corrida.

    Devuelve una fila por local y semana (14 × semanas) y los conteos del log. Con las mismas
    entradas, el resultado es siempre el mismo.
    """
    if any(week.weekday() != 0 for week in weeks):
        raise ValueError("Cada semana debe empezar en lunes (week_start de la semana ISO).")

    refined = refine_events(events)
    valid, issues = validate_events(refined, locations)
    facts, duplicates = deduplicate_facts(valid)
    facts, price_decreases = keep_price_increases(facts)

    facts = facts.assign(week_start=week_start_of(facts["timestamp"]))
    in_window = facts["week_start"].isin(set(weeks))
    outside = int((~in_window).sum())
    facts = facts[in_window]

    discarded = {DUPLICATE_FACT: duplicates, PRICE_DECREASE: price_decreases, OUTSIDE_WINDOW: outside}
    issues.update({reason: count for reason, count in discarded.items() if count})

    rows = complete_and_finalize(aggregate_weekly(facts), locations, weeks)
    waste_without_cost = int(((facts["event_type"] == WASTE) & facts["unit_cost"].isna()).sum())
    return WeeklyPerformanceResult(
        rows=rows,
        events_read=len(events),
        events_rejected=sum(issues.get(reason, 0) for reason in REJECTION_REASONS),
        events_discarded=sum(discarded.values()),
        waste_events_without_cost=waste_without_cost,
        issues=issues,
    )
