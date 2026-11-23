# `data/pipelines` folder

This folder groups **all data pipelines in the monorepo** related to the company: ingestion, ETL/ELT, cleaning, transformation, and loading into analytical or production systems.

Each subfolder or file under `data/pipelines/` should represent **one pipeline or job set** (for example `sales-etl`, `telemetry-stream`, `customer-segmentation`) and include the required configuration (scripts, orchestration, connectors, schemas, etc.).

- **Main purpose**: consolidate in one place the data movement and transformation logic that powers the company’s applications and analytics.
- **Recommendation**: document pipelines as you add them—their goal, data sources and sinks, dependencies, and how to run them in development, testing, and production.

## Pipelines

### Weekly performance per location (`weekly_location_performance`)

- **Status:** designed ([`PIPELINE_DESIGN.md`](./PIPELINE_DESIGN.md), in Spanish); the Prefect implementation comes in Parts 2 and 3.
- **Goal:** produce the "Reporte Semanal de Costo y Merma por Local" (weekly cost and waste report per location) for leadership: purchase cost, waste cost, waste ratio, stockouts and price alerts per location and ISO week.
- **Source:** `telemetry_events` (read-only, `production` only) and `locations`, in Supabase.
- **Sink:** `reporting.weekly_location_performance` (one row per location and week, upserted) and the run log `reporting.pipeline_runs`.
- **Orchestration:** a Prefect flow, Mondays at 06:00 America/Bogota, that recomputes the last 4 closed weeks; range backfills from `POST /reporting/pipeline-runs`.
- **Dependencies:** the Pandas transformations live in `data/process/`; the `services/reporting/` endpoints import the reads and the trigger from this package, never the other way round.
- **Divergences from the briefing:** [`docs/BRIEFING_DIVERGENCES.md`](../../docs/BRIEFING_DIVERGENCES.md#pipeline-de-desempeño-de-negocio) (in Spanish).

> _Spanish version: [README.es.md](./README.es.md)._
