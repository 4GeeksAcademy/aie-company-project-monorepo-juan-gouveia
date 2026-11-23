"""Transformación del "Reporte Semanal de Costo y Merma por Local" (diseño, §3.3).

Funciones puras de Pandas, sin acceso a la base ni bucles sobre filas: reciben los eventos que extrajo
el pipeline de `telemetry_events`, el catálogo `locations` y las semanas de la corrida, y devuelven las
filas de `reporting.weekly_location_performance` y los conteos que van al log de la corrida
(`reporting.pipeline_runs`). La orquestación y el acceso a la base viven en `data/pipelines/`.

Orden, el mismo que las tasks del subflow de transformación del pipeline:

1. `prepare_weekly_location_facts`: refinar → validar contra el local → deduplicar el hecho →
   filtrar las alertas de bajada → semana ISO (UTC).
2. Un cálculo por KPI del briefing ("KPIs a medir"), con el nombre de su columna:
   `compute_total_purchase_cost`, `compute_total_waste_cost`, `count_stockout_events` y
   `count_price_alert_events`.
3. `assemble_weekly_location_performance`: los 14 locales en cada semana, con ceros.
4. `compute_waste_ratio`: el ratio de merma sobre los totales de cada fila.

`build_weekly_location_performance` encadena los cuatro pasos. `detect_silent_weeks` clasifica las
semanas sin señal (captura caída o semana sin actividad).
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

    @classmethod
    def from_prepared(cls, prepared: WeeklyLocationFacts, rows: pd.DataFrame) -> WeeklyPerformanceResult:
        """Las filas finales con los conteos de la preparación."""
        return cls(
            rows=rows,
            events_read=prepared.events_read,
            events_rejected=prepared.events_rejected,
            events_discarded=prepared.events_discarded,
            waste_events_without_cost=prepared.waste_events_without_cost,
            issues=dict(prepared.issues),
        )


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


@dataclass(frozen=True)
class WeeklyLocationFacts:
    """Salida de `prepare_weekly_location_facts`: los hechos que cuentan y los conteos del log.

    `facts` tiene una fila por hecho de negocio válido de las semanas de la corrida, con `location_id`
    (el `id` entero del local), `week_start`, `event_type`, `quantity`, `unit_cost` y `variance_pct`.
    Cumple `events_read = len(facts) + events_rejected + events_discarded`.
    """

    facts: pd.DataFrame
    events_read: int
    events_rejected: int
    events_discarded: int
    waste_events_without_cost: int
    issues: dict[str, int] = field(default_factory=dict)


def prepare_weekly_location_facts(
    events: pd.DataFrame, locations: pd.DataFrame, weeks: list[date]
) -> WeeklyLocationFacts:
    """Pasos 1 a 5: de la extracción a los hechos que alimentan los KPIs.

    Refina `tags`, rechaza lo que no se puede atribuir a un local con su país y su moneda, cuenta una
    vez cada hecho, deja solo las alertas de subida y asigna la semana ISO (UTC); descarta lo que cae
    fuera de las semanas de la corrida. Un evento mal formado (un número que no lo es, un dato
    imprescindible nulo) no rompe la corrida: se rechaza como `invalid_payload` y queda en el log.
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
    return WeeklyLocationFacts(
        facts=facts[FACT_COLUMNS].reset_index(drop=True),
        events_read=len(events),
        events_rejected=sum(issues.get(reason, 0) for reason in REJECTION_REASONS),
        events_discarded=sum(discarded.values()),
        waste_events_without_cost=int(((facts["event_type"] == WASTE) & facts["unit_cost"].isna()).sum()),
        issues=issues,
    )


# --- Un cálculo por KPI ---------------------------------------------------------------------------
#
# Cada función recibe los hechos de `prepare_weekly_location_facts` y devuelve una serie por
# (`location_id`, `week_start`) con el nombre de su columna en `reporting.weekly_location_performance`.
# Solo aparecen los locales y semanas con actividad; `assemble_weekly_location_performance` completa
# el resto con ceros. Si reciben un hecho que la preparación debía haber rechazado, fallan con
# ValueError en lugar de contarlo mal: un KPI equivocado en silencio es peor que una corrida fallida.

FACT_COLUMNS = ["location_id", "week_start", "event_type", "quantity", "unit_cost", "variance_pct"]
_GROUP = ["location_id", "week_start"]


def _facts_of(facts: pd.DataFrame, event_type: str, columns: list[str], kpi: str) -> pd.DataFrame:
    """Los hechos de un tipo, tras comprobar que están las columnas que necesita el KPI."""
    missing = [column for column in [*_GROUP, "event_type", *columns] if column not in facts.columns]
    if missing:
        raise ValueError(f"{kpi}: faltan las columnas {', '.join(missing)} en los hechos.")
    return facts[facts["event_type"] == event_type]


def _invalid(kpi: str, what: str) -> ValueError:
    return ValueError(f"{kpi}: {what}; prepare_weekly_location_facts debía haberlo rechazado.")


def _sum_per_location_week(values: pd.Series, facts: pd.DataFrame, name: str) -> pd.Series:
    return values.astype("float64").groupby([facts["location_id"], facts["week_start"]]).sum().rename(name)


def _count_per_location_week(facts: pd.DataFrame, name: str) -> pd.Series:
    return facts.groupby(_GROUP).size().astype("int64").rename(name)


def compute_total_purchase_cost(facts: pd.DataFrame) -> pd.Series:
    """Costo de compra por local: Σ `quantity × unit_cost` de `inbound_order_created`, en la moneda del local."""
    kpi = "total_purchase_cost"
    inbound = _facts_of(facts, INBOUND, ["quantity", "unit_cost"], kpi)
    if not ((inbound["quantity"] > 0) & (inbound["unit_cost"] > 0)).all():
        raise _invalid(kpi, "hay entradas sin cantidad o sin coste unitario positivos")
    return _sum_per_location_week(inbound["quantity"] * inbound["unit_cost"], inbound, kpi)


def compute_total_waste_cost(facts: pd.DataFrame) -> pd.Series:
    """Costo de merma por local: Σ `quantity × unit_cost` de `stock_waste_registered`.

    Una merma sin `unit_cost` (versión 1.0.0, o un producto sin entradas con coste) cuenta 0
    (decisión P1); `prepare_weekly_location_facts` las cuenta en `waste_events_without_cost`.
    """
    kpi = "total_waste_cost"
    waste = _facts_of(facts, WASTE, ["quantity", "unit_cost"], kpi)
    unit_cost = waste["unit_cost"]
    if not ((waste["quantity"] > 0) & (unit_cost.isna() | (unit_cost > 0))).all():
        raise _invalid(kpi, "hay mermas sin cantidad positiva o con un coste unitario que no es positivo")
    return _sum_per_location_week(waste["quantity"] * unit_cost.fillna(0), waste, kpi)


def count_stockout_events(facts: pd.DataFrame) -> pd.Series:
    """Frecuencia de quiebre de stock: número de `stock_threshold_triggered` por local y semana."""
    return _count_per_location_week(_facts_of(facts, STOCKOUT, [], "stockout_events_count"), "stockout_events_count")


def count_price_alert_events(facts: pd.DataFrame) -> pd.Series:
    """Frecuencia de alertas de precio: número de `ingredient_price_variance_detected` de subida."""
    kpi = "price_alert_events_count"
    alerts = _facts_of(facts, PRICE_ALERT, ["variance_pct"], kpi)
    if not (alerts["variance_pct"] > 0).all():
        raise _invalid(kpi, "hay alertas de bajada o sin variance_pct")
    return _count_per_location_week(alerts, kpi)


def assemble_weekly_location_performance(
    total_purchase_cost: pd.Series,
    total_waste_cost: pd.Series,
    stockout_events_count: pd.Series,
    price_alert_events_count: pd.Series,
    locations: pd.DataFrame,
    weeks: list[date],
) -> pd.DataFrame:
    """Paso 8 y dimensiones: los 14 locales en cada semana de la corrida, con ceros donde no hubo actividad.

    Los importes, con 2 decimales en la moneda del local, sin convertir. `location_id` pasa a ser el
    `code` del local (decisión P2), con su `country` y su `currency`. Sin `waste_ratio`: lo añade
    `compute_waste_ratio` sobre estos totales.
    """
    grid = pd.MultiIndex.from_product([sorted(locations["id"]), sorted(weeks)], names=_GROUP)
    kpis = pd.concat(
        [total_purchase_cost, total_waste_cost, stockout_events_count, price_alert_events_count], axis=1
    )
    rows = kpis.reindex(grid, fill_value=0).fillna(0).reset_index()
    catalog = locations.set_index("id")
    rows = rows.assign(
        total_purchase_cost=rows["total_purchase_cost"].astype("float64").round(2),
        total_waste_cost=rows["total_waste_cost"].astype("float64").round(2),
        stockout_events_count=rows["stockout_events_count"].astype("int64"),
        price_alert_events_count=rows["price_alert_events_count"].astype("int64"),
        country=rows["location_id"].map(catalog["country"]),
        currency=rows["location_id"].map(catalog["currency"]),
        location_id=rows["location_id"].map(catalog["code"]),
    )
    return rows[[column for column in OUTPUT_COLUMNS if column != "waste_ratio"]].reset_index(drop=True)


def compute_waste_ratio(rows: pd.DataFrame) -> pd.DataFrame:
    """Ratio de merma: `total_waste_cost / total_purchase_cost` de cada fila, con 4 decimales.

    0 si el local no compró esa semana (no se divide entre cero). Puede superar 1: un local puede
    perder en una semana producto comprado en semanas anteriores. Devuelve las filas con las columnas
    de `reporting.weekly_location_performance`, en su orden.
    """
    kpi = "waste_ratio"
    missing = [column for column in ("total_purchase_cost", "total_waste_cost") if column not in rows.columns]
    if missing:
        raise ValueError(f"{kpi}: faltan las columnas {', '.join(missing)}.")
    purchase = pd.to_numeric(rows["total_purchase_cost"], errors="coerce")
    waste = pd.to_numeric(rows["total_waste_cost"], errors="coerce")
    if purchase.isna().any() or waste.isna().any() or (purchase < 0).any() or (waste < 0).any():
        raise ValueError(f"{kpi}: los costes de compra y de merma deben ser números no negativos.")
    ratio = (waste / purchase.where(purchase > 0)).fillna(0.0).round(4)
    return rows.assign(waste_ratio=ratio)[OUTPUT_COLUMNS]


def build_weekly_location_performance(
    events: pd.DataFrame, locations: pd.DataFrame, weeks: list[date]
) -> WeeklyPerformanceResult:
    """La transformación completa, en el orden del subflow de transformación del pipeline.

    - `events`: la extracción (`id`, `timestamp`, `event_type`, `tags`) de los cuatro tipos de evento.
    - `locations`: el catálogo (`id`, `code`, `country`, `currency`).
    - `weeks`: los lunes de las semanas de la corrida.

    Devuelve una fila por local y semana (14 × semanas) y los conteos del log. Con las mismas
    entradas, el resultado es siempre el mismo.
    """
    prepared = prepare_weekly_location_facts(events, locations, weeks)
    facts = prepared.facts
    rows = assemble_weekly_location_performance(
        compute_total_purchase_cost(facts),
        compute_total_waste_cost(facts),
        count_stockout_events(facts),
        count_price_alert_events(facts),
        locations,
        weeks,
    )
    return WeeklyPerformanceResult.from_prepared(prepared, compute_waste_ratio(rows))


# --- Señales de silencio (diseño, §12) ------------------------------------------------------------


@dataclass(frozen=True)
class SilentWeeks:
    """Semanas de la corrida sin señal: distingue una captura caída de una semana sin actividad.

    - `without_telemetry`: ningún evento de telemetría de ningún tipo (ni logins ni páginas vistas):
      lo más probable es que la captura o el almacenamiento fallaran.
    - `without_business_events`: hubo telemetría, pero ningún evento de los cuatro que alimentan los
      KPIs: puede ser una semana real sin compras ni mermas registradas en el backoffice.
    """

    without_telemetry: list[date]
    without_business_events: list[date]

    @property
    def issues(self) -> dict[str, int]:
        counts = {
            WEEKS_WITHOUT_TELEMETRY: len(self.without_telemetry),
            WEEKS_WITHOUT_BUSINESS_EVENTS: len(self.without_business_events),
        }
        return {reason: count for reason, count in counts.items() if count}


WEEKS_WITHOUT_TELEMETRY = "weeks_without_telemetry"
WEEKS_WITHOUT_BUSINESS_EVENTS = "weeks_without_business_events"


def detect_silent_weeks(
    weeks: list[date], telemetry_events_per_week: dict[date, int], business_events: pd.DataFrame
) -> SilentWeeks:
    """Clasifica cada semana de la corrida según la telemetría que llegó (pregunta "silencio vs. ausencia real").

    - `telemetry_events_per_week`: todos los eventos de telemetría del entorno, de cualquier tipo,
      por lunes de la semana (una semana sin eventos puede faltar del dict).
    - `business_events`: la extracción de los cuatro tipos de negocio (`timestamp`), antes de validar.
    """
    business_weeks = set(week_start_of(business_events["timestamp"])) if len(business_events) else set()
    without_telemetry = [week for week in sorted(weeks) if telemetry_events_per_week.get(week, 0) == 0]
    without_business = [
        week for week in sorted(weeks) if week not in without_telemetry and week not in business_weeks
    ]
    return SilentWeeks(without_telemetry, without_business)
