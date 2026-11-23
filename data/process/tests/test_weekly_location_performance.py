"""Transformación del Reporte Semanal de Costo y Merma por Local, con datos sintéticos en memoria.

Los eventos imitan la extracción de `telemetry_events` (`id`, `timestamp`, `event_type`, `tags`) con
las propiedades del catálogo de telemetría 1.3.0. Nunca se escriben en Supabase.
"""

import json
from datetime import date
from itertools import count

import pandas as pd
import pytest
from brasaland_process.weekly_location_performance import (
    OUTPUT_COLUMNS,
    build_weekly_location_performance,
    week_start_of,
)

# Las 14 sedes de la migración 004 (1–9 CO/COP, 10–14 US/USD).
CODES = [
    "medellin_centro", "medellin_laureles", "medellin_envigado", "medellin_bello", "medellin_itagui",
    "bogota_chapinero", "bogota_usaquen", "cali_granada", "barranquilla_norte",
    "miami_doral", "miami_hialeah", "miami_kendall", "orlando_international", "fort_lauderdale",
]
LOCATIONS = pd.DataFrame(
    {
        "id": range(1, 15),
        "code": CODES,
        "country": ["CO"] * 9 + ["US"] * 5,
        "currency": ["COP"] * 9 + ["USD"] * 5,
    }
)
WEEK = date(2026, 11, 16)
NEXT_WEEK = date(2026, 11, 23)
_ids = count(1)


def event(event_type, location_id=3, timestamp="2026-11-18T10:00:00.000Z", **props):
    """Un evento extraído; `country` y `currency` salen del local salvo que se indiquen."""
    country, currency = ("CO", "COP") if location_id <= 9 else ("US", "USD")
    tags = {"location_id": location_id, "country": country, "currency": currency, "environment": "production"}
    tags.update(props)
    return {"id": f"00000000-0000-4000-8000-{next(_ids):012d}", "timestamp": timestamp, "event_type": event_type, "tags": tags}


def inbound(order_id, quantity, unit_cost, **kw):
    return event("inbound_order_created", order_id=order_id, quantity=quantity, unit_cost=unit_cost, **kw)


def waste(order_id, quantity, unit_cost=None, **kw):
    props = {"order_id": order_id, "quantity": quantity, "reason": "expired"}
    if unit_cost is not None:
        props["unit_cost"] = unit_cost
    return event("stock_waste_registered", **props, **kw)


def stockout(trigger_order_id, **kw):
    return event("stock_threshold_triggered", trigger_order_id=trigger_order_id, quantity=38, threshold_quantity=40, **kw)


def price_alert(order_id, variance_pct, **kw):
    return event("ingredient_price_variance_detected", order_id=order_id, variance_pct=variance_pct, unit_cost=44000, **kw)


def run(events, weeks=(WEEK,)):
    frame = pd.DataFrame(events, columns=["id", "timestamp", "event_type", "tags"])
    return build_weekly_location_performance(frame, LOCATIONS, list(weeks))


def row(result, code, week=WEEK):
    rows = result.rows
    [match] = rows[(rows["location_id"] == code) & (rows["week_start"] == week)].to_dict(orient="records")
    return match


def test_computes_the_five_kpis_of_a_location_and_week():
    result = run(
        [
            inbound(1, 10, 36000),
            inbound(2, 30, 39000),  # compra: 10 × 36 000 + 30 × 39 000 = 1 530 000
            waste(3, 1.2, 38250),  # merma: 1,2 × 38 250 = 45 900
            stockout(3),
            price_alert(2, 12.5),
        ]
    )

    assert row(result, "medellin_envigado") == {
        "location_id": "medellin_envigado",
        "country": "CO",
        "week_start": WEEK,
        "total_purchase_cost": 1530000.0,
        "total_waste_cost": 45900.0,
        "waste_ratio": 0.03,
        "stockout_events_count": 1,
        "price_alert_events_count": 1,
        "currency": "COP",
    }


def test_one_row_per_location_and_week_with_zeros_for_the_rest():
    result = run([inbound(1, 10, 36000)], weeks=(WEEK, NEXT_WEEK))

    assert list(result.rows.columns) == OUTPUT_COLUMNS
    assert len(result.rows) == 28
    assert result.rows["location_id"].tolist()[:2] == ["medellin_centro", "medellin_centro"]
    assert row(result, "fort_lauderdale", NEXT_WEEK) == {
        "location_id": "fort_lauderdale",
        "country": "US",
        "week_start": NEXT_WEEK,
        "total_purchase_cost": 0.0,
        "total_waste_cost": 0.0,
        "waste_ratio": 0.0,
        "stockout_events_count": 0,
        "price_alert_events_count": 0,
        "currency": "USD",
    }


def test_each_location_keeps_its_own_currency_and_currencies_are_never_added():
    result = run([inbound(1, 10, 36000, location_id=1), inbound(2, 10, 4.5, location_id=10)])

    assert row(result, "medellin_centro")["total_purchase_cost"] == 360000.0
    assert row(result, "medellin_centro")["currency"] == "COP"
    assert row(result, "miami_doral")["total_purchase_cost"] == 45.0
    assert row(result, "miami_doral")["currency"] == "USD"


def test_rejects_events_that_do_not_match_their_location_or_lack_required_data():
    result = run(
        [
            inbound(1, 10, 36000, location_id=99),  # fuera del catálogo
            waste(2, 1, 4.5, location_id=11, country="CO"),  # local de US con país CO
            inbound(3, 10, 36000, currency="USD"),  # moneda que no es la del local
            event("inbound_order_created", order_id=4, quantity=10),  # entrada sin unit_cost
            waste(5, 1, 0),  # unit_cost presente pero no positivo
            stockout(None),  # quiebre sin la salida que lo provocó
            inbound(6, 10, 36000),  # el único válido
        ]
    )

    assert result.issues == {"unknown_location": 1, "country_mismatch": 1, "currency_mismatch": 1, "invalid_payload": 3}
    assert result.events_rejected == 6
    assert row(result, "medellin_envigado")["total_purchase_cost"] == 360000.0
    assert row(result, "miami_hialeah")["total_waste_cost"] == 0.0


def test_the_same_fact_emitted_twice_counts_once():
    first = inbound(7, 10, 36000, timestamp="2026-11-18T10:00:00.000Z")
    repeated = inbound(7, 10, 36000, timestamp="2026-11-18T10:00:05.000Z")

    result = run([repeated, first, stockout(9), stockout(9)])

    assert row(result, "medellin_envigado")["total_purchase_cost"] == 360000.0
    assert row(result, "medellin_envigado")["stockout_events_count"] == 1
    assert result.issues == {"duplicate_fact": 2}
    assert result.events_discarded == 2


def test_only_price_increases_count_as_alerts():
    result = run([price_alert(1, 12.5), price_alert(2, -15.0), price_alert(3, 0.0)])

    assert row(result, "medellin_envigado")["price_alert_events_count"] == 1
    assert result.issues == {"price_decrease": 2}


def test_waste_without_unit_cost_counts_as_zero_and_is_reported():
    result = run([inbound(1, 10, 36000), waste(2, 1.5), waste(3, 1, 36000)])

    assert row(result, "medellin_envigado")["total_waste_cost"] == 36000.0
    assert result.waste_events_without_cost == 1


def test_waste_ratio_is_zero_without_purchases_and_can_exceed_one():
    result = run([waste(1, 2, 36000), inbound(2, 1, 1000, location_id=1), waste(3, 3, 1000, location_id=1)])

    assert row(result, "medellin_envigado")["waste_ratio"] == 0.0
    assert row(result, "medellin_envigado")["total_waste_cost"] == 72000.0
    assert row(result, "medellin_centro")["waste_ratio"] == 3.0


def test_waste_ratio_has_four_decimals():
    result = run([inbound(1, 3, 1000), waste(2, 1, 1000)])

    assert row(result, "medellin_envigado")["waste_ratio"] == 0.3333


def test_weeks_are_iso_weeks_in_utc():
    result = run(
        [
            inbound(1, 1, 1000, timestamp="2026-11-22T23:59:59.999Z"),  # domingo: semana del 16
            inbound(2, 1, 2000, timestamp="2026-11-23T00:00:00.000Z"),  # lunes: semana del 23
        ],
        weeks=(WEEK, NEXT_WEEK),
    )

    assert row(result, "medellin_envigado", WEEK)["total_purchase_cost"] == 1000.0
    assert row(result, "medellin_envigado", NEXT_WEEK)["total_purchase_cost"] == 2000.0


def test_events_outside_the_weeks_of_the_run_are_discarded():
    result = run([inbound(1, 1, 1000), inbound(2, 1, 2000, timestamp="2026-11-23T08:00:00.000Z")])

    assert row(result, "medellin_envigado")["total_purchase_cost"] == 1000.0
    assert result.issues == {"outside_window": 1}


def test_counts_add_up_to_the_events_read():
    events = [
        inbound(1, 10, 36000),
        inbound(1, 10, 36000),
        inbound(2, 10, 36000, location_id=99),
        price_alert(3, -20.0),
        waste(4, 1),
        stockout(4),
    ]

    result = run(events)

    used = 3  # una entrada, la merma y el quiebre
    assert result.events_read == 6
    assert result.events_read == used + result.events_rejected + result.events_discarded


def test_without_events_every_location_is_zero():
    result = run([])

    assert len(result.rows) == 14
    assert result.rows[["total_purchase_cost", "total_waste_cost", "waste_ratio"]].eq(0).all().all()
    assert result.events_read == 0 and result.issues == {}


def test_the_result_does_not_depend_on_the_order_of_the_events():
    events = [inbound(1, 10, 36000), waste(2, 1.2, 38250), stockout(2), price_alert(1, 12.5), inbound(1, 10, 36000)]

    first = run(events)
    second = run(list(reversed(events)))

    pd.testing.assert_frame_equal(first.rows, second.rows)
    assert first.issues == second.issues


def test_accepts_tags_as_json_text():
    evt = inbound(1, 10, 36000)
    evt["tags"] = json.dumps(evt["tags"])

    assert row(run([evt]), "medellin_envigado")["total_purchase_cost"] == 360000.0


def test_weeks_must_start_on_monday():
    with pytest.raises(ValueError, match="lunes"):
        run([], weeks=(date(2026, 11, 17),))


def test_week_start_of_returns_the_monday_in_utc():
    stamps = pd.Series(["2026-11-22T23:59:59Z", "2026-11-23T00:00:00Z", "2026-11-22T19:30:00-05:00"])

    assert week_start_of(stamps).tolist() == [WEEK, NEXT_WEEK, NEXT_WEEK]
