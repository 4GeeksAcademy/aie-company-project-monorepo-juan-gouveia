# `data/process` folder

This folder contains **processed/intermediate data** and/or artifacts produced by pipelines (for example: clean datasets, features, aggregates, intermediate tables, or transformation outputs).

- **Main purpose**: clearly separate “raw” data from data ready for analysis, modeling, or app consumption.
- **Recommendation**: document which pipeline produces each artifact, its schema, refresh cadence, and how quality is validated (checks, constraints, data tests).

## Artifacts

### `results.csv`

- **Produced by:** [`scripts/incident-report/analyze.py`](../../scripts/incident-report/README.md), when the export prompt is answered with yes.
- **Schema:** one row per metric, with the columns `metric`, `value` and `percentage`. The list of metrics is in the script's README.
- **Refresh:** each run overwrites the previous file.
- **Quality:** the script's tests (`python -m unittest`) check the values against the dataset in `data/raw/`.
- **Versioning:** not committed to Git (it is in `.gitignore`), because every run regenerates it.

## Reusable transformations (`brasaland-process`)

This folder is also a local Python package, `brasaland-process` (imported as `brasaland_process`), with the transformations of the pipelines in [`data/pipelines/`](../pipelines/README.md). They are pure Pandas functions: they never read or write the database and use no loops over rows. The pipelines install it in editable mode with uv.

### `weekly_location_performance.py`

Transformation of the "Reporte Semanal de Costo y Merma por Local" (weekly cost and waste report per location; [design, §3.3](../pipelines/PIPELINE_DESIGN.md#33-reglas-de-la-transformación), in Spanish). `build_weekly_location_performance(events, locations, weeks)` takes the events extracted from `telemetry_events`, the `locations` catalog and the Mondays of the run's weeks, and returns:

- **`rows`:** one row per location and week (14 × weeks, with zeros where there was no activity) with the columns of `reporting.weekly_location_performance`: `location_id` (the location's `code`), `country`, `week_start`, `total_purchase_cost`, `total_waste_cost`, `waste_ratio`, `stockout_events_count`, `price_alert_events_count` and `currency`.
- **The run log counts:** `events_read`, `events_rejected`, `events_discarded`, `waste_events_without_cost` and `issues` (reason → number of events). They always add up: read = used + rejected + discarded.

| Step | Function | Rule |
|---|---|---|
| Refine | `refine_events` | One column per business property of `tags`, typed; never `user_id`, `session_id` or `request_id` |
| Validate | `validate_events` | Rejects a location outside the catalog (`unknown_location`), a country or currency that is not the location's (`country_mismatch`, `currency_mismatch`) and missing or invalid required data (`invalid_payload`) |
| Deduplicate | `deduplicate_facts` | The same fact under another `eventId` counts once: key `(event_type, order_id)`, or `trigger_order_id` for stockouts (`duplicate_fact`) |
| Alerts | `keep_price_increases` | Only increases, `variance_pct > 0` (`price_decrease`) |
| Week | `week_start_of` | Monday of the ISO week, in UTC; outside the run's weeks it is discarded (`outside_window`) |
| Purchase cost per location | `compute_total_purchase_cost` | Σ `quantity × unit_cost` of the inbound orders, per location and week |
| Waste cost per location | `compute_total_waste_cost` | Σ `quantity × unit_cost` of the waste records; waste without `unit_cost` counts 0 |
| Stockout frequency | `count_stockout_events` | Number of `stock_threshold_triggered` |
| Price alert frequency | `count_price_alert_events` | Number of price-increase alerts |
| Complete | `assemble_weekly_location_performance` | The 14 locations in every week, with zeros; amounts with 2 decimals, no currency conversion; `location_id` = the location's `code` |
| Waste ratio | `compute_waste_ratio` | `total_waste_cost / total_purchase_cost` of each row, with 4 decimals; 0 without purchases; it can exceed 1 |

- **One function per pipeline step.** `prepare_weekly_location_facts` groups the first five steps (refine to week) and returns the facts that count (`WeeklyLocationFacts`) with the log counts. Then one function per briefing KPI, named after its column: they are the tasks of the transformation subflow in [`data/pipelines/pipeline.py`](../pipelines/README.md). `build_weekly_location_performance` chains them in the same order.
- **Defensive.** A malformed event (a number that is not one, a required field that is null, empty `tags`) is rejected during preparation and recorded in the log; it does not break the run. The KPI functions raise `ValueError` if they receive a fact that preparation should have rejected (an inbound order without cost, a price-decrease alert, a negative cost): a KPI silently miscounted is worse than a failed run.
- **Silence signals.** `detect_silent_weeks` classifies the run's weeks with no telemetry event at all (`weeks_without_telemetry`, a likely capture failure) and with telemetry but no business events (`weeks_without_business_events`, a week with no recorded activity).

**Tests:** `cd data/process && uv run pytest`, with synthetic in-memory data (never in Supabase).

> _Spanish version: [README.es.md](./README.es.md)._
