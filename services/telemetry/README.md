# Telemetry analysis (`services/telemetry`)

Analysis pipeline for the telemetry **technical report**: operational metrics computed with Pandas over the `telemetry_events` table in Supabase. It is a radar for the engineering team (volume, errors, latency and authentication failures), not a business report. The design is in the [telemetry plan, section 16](../../docs/telemetry/telemetry-plan.md#16-fase-de-reporte-técnico).

> _Spanish version: [README.es.md](./README.es.md)._

## Metrics (`analysis.py`)

Each function receives a SQLAlchemy connection and the UTC window `[start, end)`, chosen by the caller, and returns a JSON-ready list of dicts. All of them group by UTC day.

| Function | Operational question | Events | Row |
|---|---|---|---|
| `events_per_day` | How much volume does the system have each day, and how much of it is warnings or errors? | All | `{date, total, info, warn, error}`; days without events are included, with zeros |
| `error_rate_by_type` | Which failure types dominate each day, and how much do they weigh on the volume? | All (the day total is the denominator) | `{date, event_type, level, count, rate}`, only `warn` or `error` types |
| `api_latency_by_route` | Which API routes respond slowly, and how slowly? | `api_latency_recorded` | `{date, method, route, samples, avg_ms, max_ms}`; mean weighted by `1/sample_rate` |
| `auth_failure_rate` | What share of login attempts fails each day? | `login_failed` and `login_succeeded` | `{date, attempts, failed, failure_rate}` |

Rates are fractions from 0 to 1 with 4 decimals, and dates are `YYYY-MM-DD`.

## How each metric is computed

Always in the same order: **load (SQL) → refine (Pandas) → convert types → group → aggregate → serve**.

- **Load.** One query per metric, with the window (`timestamp >= :start AND timestamp < :end`) and the `event_type` values it needs, selecting only the columns it uses. It never loads the whole table.
- **Refine.** Extracts the dimensions from `tags` (`route`, `method`, `duration_ms`, `sample_rate`) and drops the rows where they are missing.
- **Convert types.** `pd.to_datetime(..., utc=True)` before grouping by day: depending on the driver, `timestamp` arrives as text (SQLite) or as a date (PostgreSQL).
- **Group and aggregate.** `groupby` with `.size()`, `.agg()` and `.sum()`, without loops.

The functions only read the database: two calls with the same parameters return the same result.

## How it is consumed

It is a Python package (`brasaland-telemetry`) whose folder is the package itself: `services/telemetry/analysis.py` is imported as `brasaland_telemetry.analysis`. Its dependencies are `pandas` and `sqlalchemy`.

- **API:** declared as a local dependency in its `pyproject.toml` (`[tool.uv.sources]`, editable mode), like `packages/shared`, so `uv sync` installs it and changes show up without reinstalling.
- **Docker:** `services/Dockerfile` installs it in editable mode, and `docker-compose.yml` mounts the folder. `pandas` comes with `services/requirements.txt`.

## Tests

They run from the API, over a `telemetry_events` table in SQLite: `services/brasaland-api/tests/telemetry/test_report_analysis.py`. They cover each metric, the window bounds, empty days, the weighted mean, native types and JSON serialization, repeatability, one windowed query per metric and the absence of loops.

```bash
cd services/brasaland-api
uv run pytest tests/telemetry/test_report_analysis.py
```
