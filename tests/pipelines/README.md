# `tests/pipelines` folder

Unit tests for the data pipelines in [`data/pipelines/`](../../data/pipelines/README.md). They test the tasks in isolation: no database, no external APIs and no Prefect server.

## `test_pipeline.py`

Tests for the transformation tasks of the "Reporte Semanal de Costo y Merma por Local" pipeline (weekly cost and waste report per location; the `transform_weekly_location_performance` subflow in [`pipeline.py`](../../data/pipelines/pipeline.py)). Each test calls the task with `.fn(...)`, the function Prefect runs, using in-memory events shaped like `telemetry_events`: `id`, `timestamp`, `event_type` and the event properties in `tags`, with the fields of the mandatory metrics from the telemetry briefing.

| What is tested | Tests |
|---|---|
| One test per briefing KPI ("KPIs a medir") | Purchase cost per location (`compute_total_purchase_cost`), waste cost per location (`compute_total_waste_cost`), stockout frequency (`count_stockout_events`), price alert frequency (`count_price_alert_events`) and waste ratio (`compute_waste_ratio`) |
| The five KPIs computed by hand | One week of Medellín Centro with the arithmetic in the docstring: 850 COP of purchases, 106.25 of waste, ratio 0.125, one stockout and one alert |
| Defensive behavior | Malformed events (a number that is not one, a null cost, another location's country, empty `tags`) rejected without breaking the run; the KPI tasks and the ratio raise `ValueError` on data that should never reach them; weeks that do not start on Monday |

Test names are in Spanish, after the KPI names in the briefing.

## How to run them

The monorepo root has no Python environment: the tests use the one in `data/pipelines`, which has Prefect, Pandas and the `brasaland-pipelines` and `brasaland-process` packages. From the root:

```bash
cd data/pipelines && uv sync && cd ../..     # once
source data/pipelines/.venv/bin/activate     # on Windows: data\pipelines\.venv\Scripts\activate
python -m pytest tests/pipelines/test_pipeline.py
```

Or without activating the environment: `uv run --project data/pipelines python -m pytest tests/pipelines/test_pipeline.py`.

## Other pipeline tests

- [`data/process/tests/`](../../data/process/): the pure transformation functions, step by step.
- [`data/pipelines/tests/`](../../data/pipelines/): integration of the flow and each subflow against SQLite (run log, idempotency, retries, cache, optional steps, silence signals), the trigger and the API reads.

> _Spanish version: [README.es.md](./README.es.md)._
