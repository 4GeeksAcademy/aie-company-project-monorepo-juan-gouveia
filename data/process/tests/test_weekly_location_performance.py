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
    FACT_COLUMNS,
    OUTPUT_COLUMNS,
    assemble_weekly_location_performance,
    build_weekly_location_performance,
    compute_total_purchase_cost,
    compute_total_waste_cost,
    compute_waste_ratio,
    count_price_alert_events,
    count_stockout_events,
    detect_silent_weeks,
    prepare_weekly_location_facts,
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
    country, currency = ("CO", "COP") if location_id is None or location_id <= 9 else ("US", "USD")
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


# --- Cada paso por separado -----------------------------------------------------------------------


def prepare(events, weeks=(WEEK,)):
    frame = pd.DataFrame(events, columns=["id", "timestamp", "event_type", "tags"])
    return prepare_weekly_location_facts(frame, LOCATIONS, list(weeks))


def per_location(series, location_id=3, week=WEEK):
    return series.loc[(location_id, week)]


def test_prepare_keeps_only_the_facts_that_count_with_their_week():
    prepared = prepare([inbound(1, 10, 36000), inbound(1, 10, 36000), price_alert(2, -5.0), stockout(1)])

    assert list(prepared.facts.columns) == FACT_COLUMNS
    assert prepared.facts["event_type"].tolist() == ["inbound_order_created", "stock_threshold_triggered"]
    assert set(prepared.facts["week_start"]) == {WEEK}
    assert prepared.events_read == 4
    assert prepared.events_read == len(prepared.facts) + prepared.events_rejected + prepared.events_discarded


def test_prepare_rejects_malformed_events_instead_of_failing():
    malformed = [
        inbound(1, "diez", 36000),  # cantidad que no es un número
        inbound(2, 10, None),  # coste nulo en una entrada
        inbound(3, 1, 1, location_id=None),  # sin local
        {
            "id": "00000000-0000-4000-8000-999999999999",
            "timestamp": "2026-11-18T10:00:00Z",
            "event_type": "stock_waste_registered",
            "tags": None,  # sin propiedades
        },
    ]

    prepared = prepare([*malformed, inbound(4, 10, 36000)])

    assert prepared.events_rejected == 4
    assert prepared.issues == {"invalid_payload": 2, "unknown_location": 2}
    assert len(prepared.facts) == 1


def test_total_purchase_cost_adds_quantity_times_unit_cost_of_the_inbound_orders():
    facts = prepare(
        [
            inbound(1, 10, 36000),
            inbound(2, 2.5, 4000),  # 360 000 + 10 000
            waste(3, 1, 36000),  # una merma no es una compra
            inbound(4, 3, 1000, location_id=1),
        ]
    ).facts

    total = compute_total_purchase_cost(facts)

    assert total.name == "total_purchase_cost"
    assert per_location(total) == 370000.0
    assert per_location(total, location_id=1) == 3000.0


def test_total_waste_cost_counts_waste_without_unit_cost_as_zero():
    facts = prepare([waste(1, 1.2, 38250), waste(2, 4), inbound(3, 1, 1000)]).facts

    total = compute_total_waste_cost(facts)

    assert total.name == "total_waste_cost"
    assert per_location(total) == 45900.0  # 1,2 × 38 250; la merma sin coste suma 0


def test_stockout_and_price_alert_counts_per_location_and_week():
    facts = prepare(
        [stockout(1), stockout(2), stockout(3, location_id=10), price_alert(4, 12.5), price_alert(5, 30.0)],
    ).facts

    stockouts = count_stockout_events(facts)
    alerts = count_price_alert_events(facts)

    assert (stockouts.name, alerts.name) == ("stockout_events_count", "price_alert_events_count")
    assert per_location(stockouts) == 2
    assert per_location(stockouts, location_id=10) == 1
    assert per_location(alerts) == 2


def test_kpis_of_a_week_without_facts_are_empty():
    facts = prepare([]).facts

    for kpi in (compute_total_purchase_cost, compute_total_waste_cost, count_stockout_events, count_price_alert_events):
        assert kpi(facts).empty


def test_kpis_refuse_facts_that_should_have_been_rejected():
    facts = prepare([inbound(1, 10, 36000), waste(2, 1, 1000), price_alert(3, 12.5)]).facts

    no_cost = facts.assign(unit_cost=facts["unit_cost"].where(facts["event_type"] != "inbound_order_created"))
    with pytest.raises(ValueError, match="total_purchase_cost"):
        compute_total_purchase_cost(no_cost)

    negative_waste = facts.assign(unit_cost=-facts["unit_cost"])
    with pytest.raises(ValueError, match="total_waste_cost"):
        compute_total_waste_cost(negative_waste)

    price_drop = facts.assign(variance_pct=-facts["variance_pct"])
    with pytest.raises(ValueError, match="price_alert_events_count"):
        count_price_alert_events(price_drop)

    with pytest.raises(ValueError, match="faltan las columnas quantity"):
        compute_total_purchase_cost(facts.drop(columns="quantity"))


def test_assemble_puts_every_location_in_every_week_with_its_currency():
    facts = prepare([inbound(1, 10, 36000.004)], weeks=(WEEK, NEXT_WEEK)).facts

    rows = assemble_weekly_location_performance(
        compute_total_purchase_cost(facts),
        compute_total_waste_cost(facts),
        count_stockout_events(facts),
        count_price_alert_events(facts),
        LOCATIONS,
        [WEEK, NEXT_WEEK],
    )

    assert len(rows) == 28
    assert "waste_ratio" not in rows.columns
    envigado = rows[(rows["location_id"] == "medellin_envigado") & (rows["week_start"] == WEEK)].iloc[0]
    assert envigado["total_purchase_cost"] == 360000.04  # 2 decimales
    assert (envigado["country"], envigado["currency"]) == ("CO", "COP")
    doral = rows[(rows["location_id"] == "miami_doral") & (rows["week_start"] == NEXT_WEEK)].iloc[0]
    assert (doral["total_purchase_cost"], doral["stockout_events_count"], doral["currency"]) == (0.0, 0, "USD")


def test_waste_ratio_matches_the_briefing_definition_for_known_totals():
    # Briefing, "Ratio de merma": total_waste_cost / total_purchase_cost, y 0 si no hubo compras.
    rows = pd.DataFrame(
        {
            "location_id": ["medellin_centro", "medellin_laureles", "miami_doral", "fort_lauderdale"],
            "country": ["CO", "CO", "US", "US"],
            "week_start": [WEEK] * 4,
            "total_purchase_cost": [850.0, 1530000.0, 100.0, 0.0],
            "total_waste_cost": [106.25, 45900.0, 250.0, 20.0],
            "stockout_events_count": [1, 0, 0, 0],
            "price_alert_events_count": [1, 0, 0, 0],
            "currency": ["COP", "COP", "USD", "USD"],
        }
    )

    result = compute_waste_ratio(rows)

    assert list(result.columns) == OUTPUT_COLUMNS
    # 106,25 / 850 = 0,125; 45 900 / 1 530 000 = 0,03; 250 / 100 = 2,5 (supera 1); sin compras, 0.
    assert result["waste_ratio"].tolist() == [0.125, 0.03, 2.5, 0.0]


def test_waste_ratio_refuses_negative_or_non_numeric_costs():
    with pytest.raises(ValueError, match="waste_ratio"):
        compute_waste_ratio(pd.DataFrame({"total_purchase_cost": [100.0], "total_waste_cost": [-1.0]}))

    with pytest.raises(ValueError, match="no negativos"):
        compute_waste_ratio(pd.DataFrame({"total_purchase_cost": ["cien"], "total_waste_cost": [1.0]}))

    with pytest.raises(ValueError, match="faltan las columnas total_waste_cost"):
        compute_waste_ratio(pd.DataFrame({"total_purchase_cost": [1.0]}))


def test_build_chains_the_steps_with_the_counts_of_the_preparation():
    events = [inbound(1, 10, 36000), inbound(1, 10, 36000), waste(2, 1), stockout(2), price_alert(1, 12.5)]

    result = run(events)
    prepared = prepare(events)

    assert (result.events_read, result.events_rejected, result.events_discarded) == (
        prepared.events_read,
        prepared.events_rejected,
        prepared.events_discarded,
    )
    assert result.waste_events_without_cost == prepared.waste_events_without_cost == 1
    assert result.issues == prepared.issues == {"duplicate_fact": 1}


def test_silent_weeks_tell_a_capture_failure_from_a_week_without_activity():
    weeks = [date(2026, 11, 2), date(2026, 11, 9), WEEK]
    telemetry = {date(2026, 11, 9): 40, WEEK: 120}  # la semana del 2 no tiene ningún evento
    business = pd.DataFrame(
        [inbound(1, 10, 36000, timestamp="2026-11-18T10:00:00Z")], columns=["id", "timestamp", "event_type", "tags"]
    )

    silent = detect_silent_weeks(weeks, telemetry, business)

    assert silent.without_telemetry == [date(2026, 11, 2)]
    assert silent.without_business_events == [date(2026, 11, 9)]
    assert silent.issues == {"weeks_without_telemetry": 1, "weeks_without_business_events": 1}


def test_no_silent_weeks_means_no_issues():
    business = pd.DataFrame([inbound(1, 1, 1)], columns=["id", "timestamp", "event_type", "tags"])

    assert detect_silent_weeks([WEEK], {WEEK: 3}, business).issues == {}
    assert detect_silent_weeks([WEEK], {}, business.iloc[0:0]).without_telemetry == [WEEK]
