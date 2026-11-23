# `data/pipelines` folder

This folder groups **all data pipelines in the monorepo** related to the company: ingestion, ETL/ELT, cleaning, transformation, and loading into analytical or production systems.

Each subfolder or file under `data/pipelines/` should represent **one pipeline or job set** (for example `sales-etl`, `telemetry-stream`, `customer-segmentation`) and include the required configuration (scripts, orchestration, connectors, schemas, etc.).

- **Main purpose**: consolidate in one place the data movement and transformation logic that powers the company’s applications and analytics.
- **Recommendation**: document pipelines as you add them—their goal, data sources and sinks, dependencies, and how to run them in development, testing, and production.

## Pipelines

### Weekly performance per location (`weekly_location_performance`)

- **Status:** implemented with Prefect (Part 2); Part 3 will split the stages into subflows and add the dashboard. Design, adjustments and verification in [`PIPELINE_DESIGN.md`](./PIPELINE_DESIGN.md) (in Spanish).
- **Goal:** produce the "Reporte Semanal de Costo y Merma por Local" (weekly cost and waste report per location) for leadership: purchase cost, waste cost, waste ratio, stockouts and price alerts per location and ISO week.
- **Source:** `telemetry_events` (read-only, `production` only) and `locations`, in Supabase.
- **Sink:** `reporting.weekly_location_performance` (one row per location and week, upserted) and the run log `reporting.pipeline_runs`.
- **Orchestration:** the `weekly_location_performance_flow` flow in [`pipeline.py`](./pipeline.py), Mondays at 06:00 America/Bogota, recomputes the last 4 closed weeks; range backfills from the CLI or `POST /reporting/pipeline-runs`.
- **Dependencies:** the Pandas transformations live in `data/process/`; the `services/reporting/` endpoints import the reads and the trigger from this package, never the other way round.
- **Divergences from the briefing:** [design](../../docs/BRIEFING_DIVERGENCES.md#pipeline-de-desempeño-de-negocio) and [implementation](../../docs/BRIEFING_DIVERGENCES.md#pipeline-de-desempeño-de-negocio-resiliente), in `docs/BRIEFING_DIVERGENCES.md` (in Spanish).

#### How to run it

```bash
cd data/pipelines
uv sync                       # the package, data/process, Prefect (orchestration group) and pytest
cp .env.example .env          # REPORTING_DATABASE_URL: Supabase Session pooler with the reporting_pipeline role
uv run python pipeline.py     # one run: the last 4 closed weeks of production
uv run pytest                 # tests: the flow against SQLite, the trigger and the reads
```

- **Requirements:** migration [`005_reporting.sql`](../../services/brasaland-api/migrations/005_reporting.sql) run in Supabase, and a login for the `reporting_pipeline` role (instructions in its header).
- **More commands:** backfill (`--week-from`, `--week-to`), verification with the local backoffice events (`--environment development --include-current-week`), the Monday deployment (`--serve`) and Prefect blocks (`--register-blocks`). They are in §10 of the design, with the schedule.
- **With Docker:** `docker compose up --build` at the root starts `prefect-server` (http://localhost:4200) and `reporting-pipeline`, which serves the deployment using `data/pipelines/.env`.
- **Prefect server:** without `PREFECT_API_URL`, each command starts a temporary one. On Windows, that server logs internal errors from its SQLite database (`UNIQUE constraint failed: task_run_state`) that do not affect the run; with `PREFECT_API_URL=http://localhost:4200/api` they do not appear.
- **Cache:** the transformation and the location catalog are reused for 1 hour within the same process (Prefect's result storage); a run from the host does not reuse the container's.
- **Files from each run:** the extract in [`data/raw/telemetry_events/`](../raw/README.md) and the checks in [`data/eval/weekly_location_performance/`](../eval/README.md), outside Git.

> _Spanish version: [README.es.md](./README.es.md)._
