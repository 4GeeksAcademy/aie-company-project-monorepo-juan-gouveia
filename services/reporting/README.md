# Business reports (`services/reporting`)

Endpoints of the **Reporte Semanal de Costo y Merma por Local** (weekly cost and waste report per location), the output of the [`data/pipelines`](../../data/pipelines/README.md) pipeline ([design](../../data/pipelines/PIPELINE_DESIGN.md), §6, in Spanish). Separate from the engineering technical report (`services/telemetry`, `GET /telemetry/report`).

> _Spanish version: [README.es.md](./README.es.md)._

## Routes

The three routes of the briefing, literal and outside `/api/v1`, like the telemetry ones. They follow the API conventions: Bearer token and `{"error": {"code", "message"}}` errors.

| Route | Role | What it does | Imports from `data/pipelines` |
|---|---|---|---|
| `GET /reporting/weekly-location-performance` | `admin`, `manager` | The KPIs of every location in a week: the dashboard feed | `repository.read_weekly_location_performance` |
| `GET /reporting/pipeline-runs/latest` | `admin`, `manager` | Status and metadata of the latest run | `repository.read_latest_pipeline_run` |
| `POST /reporting/pipeline-runs` | `admin` | Asks Prefect for a manual run and answers 202, without waiting | `trigger.trigger_pipeline_run` |

### `GET /reporting/weekly-location-performance`

- **Parameter:** optional `week_start` (`YYYY-MM-DD`, a Monday). Without it, the most recent computed week.
- **Response:** the briefing's shape (§6), plus `location_name` for each location. Amounts are in the location's currency, never converted (see the Spanish README for an example).
- **Cache:** 5 minutes per week (`X-Cache: HIT` or `MISS`). The run writes from another process, so new data may take up to 5 minutes to show.
- **Errors:** 422 `invalid_week_start` (not a Monday); 404 `week_not_computed`; 503 `reporting_unavailable` (database down or migration 005 missing).

### `GET /reporting/pipeline-runs/latest`

The latest row of `reporting.pipeline_runs`: `id`, `trigger`, `status` (`pending`, `running`, `completed`, `failed`), `week_from`, `week_to`, `created_at`, `started_at`, `finished_at`, `events_read`, `events_rejected`, `events_discarded`, `waste_events_without_cost`, `issues`, `rows_written`, `failed_task` and `error_message`. No cache. 404 `no_pipeline_runs` if it never ran.

### `POST /reporting/pipeline-runs`

- **Optional body:** `{"week_from": "2026-09-07", "week_to": "2026-11-16"}`. Without a body, the last 4 closed weeks.
- **What it does:** records the run as `pending` and creates a flow run of the `weekly-location-performance/weekly` deployment on the Prefect server (`PREFECT_API_URL`). The `reporting-pipeline` service (`pipeline.py --serve`) runs it. **The API never runs the ETL.**
- **202 response:** the `pending` run. Follow it with `GET /reporting/pipeline-runs/latest`.
- **Errors:** 422 `invalid_week_range`; 409 `pipeline_run_in_progress`; 503 `orchestrator_unavailable` (no `PREFECT_API_URL`, server down or deployment not served; if the run was already recorded, it is closed as `failed`).

## How it is built

- **HTTP only.** `router.py` authenticates, validates and serializes; `schemas.py` holds the response and input models. Reading `reporting.*` and triggering runs live in `data/pipelines`, the package that owns those tables.
- **No Prefect.** The API never imports Prefect: on import, Prefect reconfigures the process logging (the root and uvicorn loggers). `trigger.py` talks to the Prefect REST API with httpx, and `brasaland-pipelines` does not declare Prefect as a package dependency (it is in its `orchestration` group). A test guards this.
- **Local package** `brasaland-reporting` (imported as `brasaland_reporting`), installed in the API in editable mode and mounted in `app/main.py`. It only works inside the API: it uses its `ApiError`, authentication, database and `TTLCache`.
- **Tests:** `tests/reporting/` in the API (`uv run pytest tests/reporting`).
