# `services/jobs` — state control for scheduled jobs

_[Versión en español](./README.es.md)._

Python package `brasaland-jobs` (imported as `brasaland_jobs`) holding the state logic of the nightly telemetry script ([`scripts/nightly_export.py`](../../scripts/README.md#nightly_exportpy), ticket #DEV-53). It records every execution in the Supabase table `ops.job_runs` ([migration 006](../brasaland-api/migrations/006_job_runs.sql)). It is not a service that runs on its own, and it does not depend on the API or on FastAPI: the script is an independent process.

## The state machine

```
pending → processing → completed
                    ↘ failed
```

| Status | When |
| --- | --- |
| `pending` | The row is created, before starting |
| `processing` | Before doing any work. **It is the lock** |
| `completed` | Only if everything finished well |
| `failed` | On any exception, with the message in `error_message` |

- **Lock:** the `processing` status itself, with no separate table or column. The partial unique index `uq_job_runs_one_processing` allows a single `processing` row per job, so even if two instances start at the same instant, the second transition fails atomically and that instance aborts.
- **Idempotency:** by `(job_name, target_date)`. If there is already a `completed` execution for the date, it is not repeated.
- **Skips and cancellations:** a duplicate skip and a lock cancellation only go to the log (`INFO`), with no new row: running twice leaves `job_runs` as running once. The instance that loses the index race had already created its `pending` row; it closes it as `failed` with `lock_held: …`.
- **No zombie rows:** a `try/except/finally` moves the row to `failed` on any exception, including `KeyboardInterrupt` and `SystemExit` (the script turns `SIGTERM` into `SystemExit`). A `SIGKILL` skips the `finally`: the next execution closes as `failed` (`abandoned: …`) the open rows older than `NIGHTLY_STALE_MINUTES` (120 by default).
- **`job_runs` is not `reporting.pipeline_runs`:** `job_runs` records orchestration (export, pipeline trigger, lock and idempotency); the pipeline still records its ETL in `pipeline_runs`.

## Modules

- **[`job_runner.py`](./job_runner.py):** the `ops.job_runs` table (as in 006), the queries `has_processing_lock`, `has_completed_for_date`, `get_run` and `list_runs`, the transitions `create_run`, `start_run` (raises `LockHeld` if another instance holds the lock), `complete_run` and `fail_run`, `abandon_stale_runs`, and `run_job`, which runs a piece of work through the whole state machine and returns `completed`, `skipped` or `cancelled` (a failure propagates).
- **[`logs.py`](./logs.py):** the jobs' log format, with a UTC timestamp, level, job name and resulting status on every line:

```
2026-11-24T12:12:15Z | INFO | nightly_export | processing | target_date=2026-11-23 | Inicio de la ejecución a337f563-…
```

## Environment

```bash
cd services/jobs
uv sync               # the package, the script group (pipeline, Prefect 3.9.4 and python-dotenv) and pytest
uv run pytest         # 29 tests, with SQLite (no Supabase)
```

- **`script` group:** the nightly script's environment. It includes `brasaland-pipelines` (from `data/pipelines`, editable) because the script computes the weeks with `compute_weeks` and launches the pipeline as a subprocess with this same interpreter. Installing just the package brings only SQLAlchemy and psycopg2.
- **Configuration:** `.env` in this folder (not versioned), from [`.env.example`](./.env.example). The only required variable is `JOBS_DATABASE_URL`, the `nightly_jobs` role's connection string. How to create the role and its login: [API README, "`ops` schema"](../brasaland-api/README.md#ops-schema-nightly-telemetry-script).
- **Docker:** [`Dockerfile`](./Dockerfile) is the image of the `nightly-scheduler` service (supercronic with the script's crontab); it is built from the root `docker-compose.yml`.
