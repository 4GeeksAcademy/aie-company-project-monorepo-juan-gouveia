"""Tests unitarios de las tasks de transformación del pipeline del Reporte Semanal de Costo y Merma por Local.

Cada test llama a una task del subflow `transform_weekly_location_performance` de
`data/pipelines/pipeline.py` con `.fn(...)`: la función de la task, sin servidor de Prefect, sin base de
datos y sin APIs externas. Los datos son eventos en memoria con la forma de `telemetry_events`
(`id`, `timestamp`, `event_type` y las propiedades del evento en `tags`), con los campos de las métricas
obligatorias del BRIEFING de telemetría.

Ejecución, desde la raíz del monorepo, con el entorno de data/pipelines (ver tests/pipelines/README.md):

    python -m pytest tests/pipelines/test_pipeline.py
"""

from datetime import date
from itertools import count

import pandas as pd
import pytest
from brasaland_pipelines.pipeline import (
    assemble_weekly_location_performance,
    compute_total_purchase_cost,
    compute_total_waste_cost,
    compute_waste_ratio,
    count_price_alert_events,
    count_stockout_events,
    prepare_weekly_location_facts,
)

# Semana ISO del 16 al 22 de noviembre de 2026 (week_start = el lunes, en UTC).
WEEK = date(2026, 11, 16)

# Tres de los 14 locales del catálogo `locations`: dos en Colombia (COP) y uno en Florida (USD).
LOCATIONS = pd.DataFrame(
    {
        "id": [1, 6, 10],
        "code": ["medellin_centro", "bogota_chapinero", "miami_doral"],
        "country": ["CO", "CO", "US"],
        "currency": ["COP", "COP", "USD"],
    }
)
MEDELLIN_CENTRO, BOGOTA_CHAPINERO, MIAMI_DORAL = 1, 6, 10

_ids = count(1)


# --- Eventos de telemetría en memoria -------------------------------------------------------------


def telemetry_event(event_type, location_id, timestamp="2026-11-18T15:00:00.000Z", **properties):
    """Una fila de `telemetry_events` como la lee la extracción: el envelope y las propiedades en `tags`."""
    country, currency = ("US", "USD") if location_id == MIAMI_DORAL else ("CO", "COP")
    tags = {
        "location_id": location_id,
        "country": country,
        "currency": currency,
        **properties,
        "schema_version": "1.0.0",
        "environment": "production",
    }
    return {
        "id": f"00000000-0000-4000-8000-{next(_ids):012d}",
        "timestamp": timestamp,
        "event_type": event_type,
        "tags": tags,
    }


def inbound_order_created(location_id, order_id, quantity, unit_cost, **extra):
    return telemetry_event(
        "inbound_order_created", location_id, order_id=order_id, quantity=quantity, unit_cost=unit_cost, unit="kg", **extra
    )


def stock_waste_registered(location_id, order_id, quantity, unit_cost=None):
    properties = {"order_id": order_id, "quantity": quantity, "unit": "kg", "reason": "expired"}
    if unit_cost is not None:
        properties["unit_cost"] = unit_cost
    return telemetry_event("stock_waste_registered", location_id, **{**properties, "schema_version": "1.1.0"})


def stock_threshold_triggered(location_id, trigger_order_id):
    return telemetry_event(
        "stock_threshold_triggered", location_id, trigger_order_id=trigger_order_id, quantity=35, threshold_quantity=40
    )


def ingredient_price_variance_detected(location_id, order_id, variance_pct):
    return telemetry_event(
        "ingredient_price_variance_detected", location_id, order_id=order_id, variance_pct=variance_pct, unit_cost=25
    )


def extracted(*events):
    """La salida de la extracción: un DataFrame con las columnas de `telemetry_events` que se leen."""
    return pd.DataFrame(list(events), columns=["id", "timestamp", "event_type", "tags"])


def facts_of(*events):
    """Los hechos que preparan las tasks de KPI, con la task de preparación."""
    return prepare_weekly_location_facts.fn(extracted(*events), LOCATIONS, [WEEK]).facts


def kpi(series, location_id):
    return series.loc[(location_id, WEEK)]


# --- Un test por KPI del briefing -----------------------------------------------------------------


def test_costo_de_compra_por_local_suma_cantidad_por_costo_unitario_de_las_entradas():
    facts = facts_of(
        inbound_order_created(MEDELLIN_CENTRO, order_id=1, quantity=10, unit_cost=36000),
        inbound_order_created(MEDELLIN_CENTRO, order_id=2, quantity=2.5, unit_cost=4000),
        inbound_order_created(MIAMI_DORAL, order_id=3, quantity=50, unit_cost=2),
        stock_waste_registered(MEDELLIN_CENTRO, order_id=4, quantity=1, unit_cost=36000),  # no es una compra
    )

    total_purchase_cost = compute_total_purchase_cost.fn(facts)

    assert kpi(total_purchase_cost, MEDELLIN_CENTRO) == 10 * 36000 + 2.5 * 4000  # 370 000 COP
    assert kpi(total_purchase_cost, MIAMI_DORAL) == 50 * 2  # 100 USD, sin sumar con los COP


def test_costo_de_merma_por_local_cuenta_con_coste_cero_la_merma_sin_unit_cost():
    facts = facts_of(
        stock_waste_registered(MEDELLIN_CENTRO, order_id=1, quantity=1.2, unit_cost=38250),
        stock_waste_registered(MEDELLIN_CENTRO, order_id=2, quantity=4),  # versión 1.0.0: sin coste
    )

    total_waste_cost = compute_total_waste_cost.fn(facts)

    assert kpi(total_waste_cost, MEDELLIN_CENTRO) == pytest.approx(1.2 * 38250)  # 45 900 COP


def test_frecuencia_de_quiebre_de_stock_cuenta_un_quiebre_por_salida():
    facts = facts_of(
        stock_threshold_triggered(BOGOTA_CHAPINERO, trigger_order_id=7),
        stock_threshold_triggered(BOGOTA_CHAPINERO, trigger_order_id=8),
        stock_threshold_triggered(BOGOTA_CHAPINERO, trigger_order_id=8),  # el mismo quiebre, emitido dos veces
    )

    stockout_events_count = count_stockout_events.fn(facts)

    assert kpi(stockout_events_count, BOGOTA_CHAPINERO) == 2


def test_frecuencia_de_alertas_de_precio_cuenta_solo_las_subidas():
    facts = facts_of(
        ingredient_price_variance_detected(MEDELLIN_CENTRO, order_id=1, variance_pct=25.0),
        ingredient_price_variance_detected(MEDELLIN_CENTRO, order_id=2, variance_pct=-12.0),  # bajada: no cuenta
    )

    price_alert_events_count = count_price_alert_events.fn(facts)

    assert kpi(price_alert_events_count, MEDELLIN_CENTRO) == 1


def test_ratio_de_merma_es_cero_sin_compras_y_puede_superar_uno():
    rows = pd.DataFrame(
        {
            "location_id": ["medellin_centro", "bogota_chapinero", "miami_doral"],
            "country": ["CO", "CO", "US"],
            "week_start": [WEEK] * 3,
            "total_purchase_cost": [0.0, 1000.0, 100.0],
            "total_waste_cost": [500.0, 3000.0, 1.0],
            "stockout_events_count": [0, 0, 0],
            "price_alert_events_count": [0, 0, 0],
            "currency": ["COP", "COP", "USD"],
        }
    )

    waste_ratio = compute_waste_ratio.fn(rows)["waste_ratio"].tolist()

    # Sin compras, 0 (no se divide entre cero); 3000 / 1000 = 3 (merma de compras anteriores); 4 decimales.
    assert waste_ratio == [0.0, 3.0, 0.01]


# --- Un KPI calculado a mano según su definición en el BRIEFING -----------------------------------


def test_los_kpis_de_una_semana_coinciden_con_el_calculo_a_mano_del_briefing():
    """Medellín Centro, semana del 16 de noviembre de 2026, con las definiciones de "KPIs a medir".

    - Costo de compra por local: 3 entradas de 10 kg a 20 COP y 1 de 10 kg a 25 COP
      → 10×20 + 10×20 + 10×20 + 10×25 = 850 COP.
    - Costo de merma por local: 5 kg a 21,25 COP (coste medio ponderado de las entradas) → 106,25 COP.
    - Ratio de merma: 106,25 / 850 = 0,125.
    - Frecuencia de quiebre de stock: 1. Frecuencia de alertas de precio: 1 (subida del 25 %).
    """
    facts = facts_of(
        inbound_order_created(MEDELLIN_CENTRO, order_id=1, quantity=10, unit_cost=20),
        inbound_order_created(MEDELLIN_CENTRO, order_id=2, quantity=10, unit_cost=20),
        inbound_order_created(MEDELLIN_CENTRO, order_id=3, quantity=10, unit_cost=20),
        inbound_order_created(MEDELLIN_CENTRO, order_id=4, quantity=10, unit_cost=25),
        ingredient_price_variance_detected(MEDELLIN_CENTRO, order_id=4, variance_pct=25.0),
        stock_waste_registered(MEDELLIN_CENTRO, order_id=5, quantity=5, unit_cost=21.25),
        stock_threshold_triggered(MEDELLIN_CENTRO, trigger_order_id=5),
    )

    rows = assemble_weekly_location_performance.fn(
        compute_total_purchase_cost.fn(facts),
        compute_total_waste_cost.fn(facts),
        count_stockout_events.fn(facts),
        count_price_alert_events.fn(facts),
        LOCATIONS,
        [WEEK],
    )
    rows = compute_waste_ratio.fn(rows)

    medellin_centro = rows[rows["location_id"] == "medellin_centro"].iloc[0].to_dict()
    assert medellin_centro == {
        "location_id": "medellin_centro",
        "country": "CO",
        "week_start": WEEK,
        "total_purchase_cost": 850.0,
        "total_waste_cost": 106.25,
        "waste_ratio": 0.125,
        "stockout_events_count": 1,
        "price_alert_events_count": 1,
        "currency": "COP",
    }
    # Los locales sin actividad también aparecen, en cero y en su propia moneda.
    miami_doral = rows[rows["location_id"] == "miami_doral"].iloc[0]
    assert (miami_doral["total_purchase_cost"], miami_doral["waste_ratio"], miami_doral["currency"]) == (0.0, 0.0, "USD")


# --- Comportamiento defensivo ante entradas inválidas ---------------------------------------------


def test_la_preparacion_rechaza_eventos_mal_formados_sin_romper_la_corrida():
    malformed = extracted(
        inbound_order_created(MEDELLIN_CENTRO, order_id=1, quantity="diez", unit_cost=36000),  # tipo incorrecto
        inbound_order_created(MEDELLIN_CENTRO, order_id=2, quantity=10, unit_cost=None),  # nulo donde no se espera
        inbound_order_created(MIAMI_DORAL, order_id=3, quantity=10, unit_cost=4, country="CO"),  # país de otro local
        {"id": "00000000-0000-4000-8000-999999999999", "timestamp": "2026-11-18T15:00:00Z",
         "event_type": "stock_waste_registered", "tags": None},  # sin propiedades
        inbound_order_created(MEDELLIN_CENTRO, order_id=4, quantity=10, unit_cost=36000),  # el único válido
    )

    prepared = prepare_weekly_location_facts.fn(malformed, LOCATIONS, [WEEK])

    assert prepared.events_read == 5
    assert prepared.events_rejected == 4
    assert prepared.issues == {"invalid_payload": 2, "country_mismatch": 1, "unknown_location": 1}
    assert kpi(compute_total_purchase_cost.fn(prepared.facts), MEDELLIN_CENTRO) == 360000.0


def test_las_tasks_de_kpi_fallan_ante_un_hecho_que_debia_rechazarse():
    facts = facts_of(inbound_order_created(MEDELLIN_CENTRO, order_id=1, quantity=10, unit_cost=36000))
    without_cost = facts.assign(unit_cost=None)

    # Un KPI contado mal en silencio es peor que una corrida fallida.
    with pytest.raises(ValueError, match="total_purchase_cost"):
        compute_total_purchase_cost.fn(without_cost)


def test_el_ratio_de_merma_rechaza_costes_negativos_o_que_no_son_numeros():
    with pytest.raises(ValueError, match="waste_ratio"):
        compute_waste_ratio.fn(pd.DataFrame({"total_purchase_cost": [100.0], "total_waste_cost": [-5.0]}))
    with pytest.raises(ValueError, match="waste_ratio"):
        compute_waste_ratio.fn(pd.DataFrame({"total_purchase_cost": ["cien"], "total_waste_cost": [5.0]}))


def test_la_preparacion_exige_semanas_que_empiecen_en_lunes():
    with pytest.raises(ValueError, match="lunes"):
        prepare_weekly_location_facts.fn(extracted(), LOCATIONS, [date(2026, 11, 18)])
