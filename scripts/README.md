# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## Available scripts

| Script | What it does |
|---|---|
| [`incident-report/`](./incident-report/README.md) | Validates and summarizes the operational incidents CSV, and exports the metrics to `data/process/results.csv` (Python, no dependencies; the rules live in `packages/shared`). |
| [`seed_incidents.py`](./seed_incidents.py) | Loads the historical incidents CSV into the API's incident manager: validates each row with the `packages/shared` rules, transforms it to the manager's model (status, category, title, date and location) with origin `customer`, and inserts only the rows that were not loaded before. It needs the API environment (TinyDB). |
| [`seed_volume.py`](./seed_volume.py) | Loads realistic volume to measure API performance (caching task): 150 ingredients and about 21,000 orders in Supabase, and 10,000 incidents in TinyDB. Everything is marked (`VOL-`) and `--clear` removes it without touching real data. It needs the API environment and its `.env`. |
| [`nightly_export.py`](./nightly_export.py) | Nightly telemetry script (ticket #DEV-53): exports the previous day's (UTC) `telemetry_events` to CSV in `data/raw/telemetry_exports/`, launches the business performance pipeline as a subprocess and records every execution in `ops.job_runs`, with a lock and per-date idempotency. The `nightly-scheduler` service triggers it every night (crontab in [`nightly_export.crontab`](./nightly_export.crontab)). It needs the `services/jobs` environment and its `.env`. |

## `seed_incidents.py`

From the repository root:

```bash
uv run --project services/brasaland-api python scripts/seed_incidents.py            # data/raw/incidents-brasaland.csv
uv run --project services/brasaland-api python scripts/seed_incidents.py other.csv  # another file
```

- **Where it writes:** to the API's TinyDB file (`services/brasaland-api/storage/brasaland-db.json`), or to `BRASALAND_DB_PATH` if it is set. It can run while the API is running.
- **Transformations (incident manager briefing):** `OPEN`/`CLOSED`/`DISCARDED` → `open`/`resolved`/`discarded`; CSV categories to the manager's (`FOOD_QUALITY` → `customer_complaint`); `title` is the first 120 characters of `description`; `date` is midnight UTC for `created_at` and `updated_at`; `location_id` → `branch` (`COL-10` and unmapped locations → `central`); `origin` is always `customer`.
- **Invalid rows:** rows that break any analyzer rule (or cannot be transformed) are not inserted and are listed at the end with their row and reason.
- **Idempotent:** it stores the `incident_id` of each loaded row in the `incident_seed_log` table (not in the incident). A second run inserts 0 and counts them as "already loaded".
- **Errors:** if the CSV cannot be read, or the database cannot be opened, is not valid JSON or cannot be written (for example, a full disk), it prints the reason and exits with code 1, without a traceback. A corrupt database is left untouched; after a write failure, running it again does not duplicate anything. The final report shows the absolute path of the database on purpose, so the operator can confirm which file was changed (`BRASALAND_DB_PATH` can point anywhere).
- **Result with the briefing CSV:** 100 rows, 96 inserted and 4 invalid (`BRS-000044`, `BRS-000049`, `BRS-000079` and `BRS-000086`). Afterwards, `/api/incidents/summary` gives `open` 32, `resolved` 50, `discarded` 14 and `customer_complaint` 48, `equipment_failure` 17, `supply_issue` 22, `staff_issue` 9, the values the briefing expects.

Tests (20):

```bash
uv run --project services/brasaland-api python -m unittest scripts/test_seed_incidents.py
```

> _Spanish version: [README.es.md](./README.es.md)._

## `seed_volume.py`

From the repository root, **with the API stopped** (it writes to `brasaland-db.json` in bulk):

```bash
uv run --project services/brasaland-api --env-file services/brasaland-api/.env python scripts/seed_volume.py          # load
uv run --project services/brasaland-api --env-file services/brasaland-api/.env python scripts/seed_volume.py --clear  # remove
```

- **Inventory (Supabase):** 150 ingredients (75 from Colombia with Spanish names and 75 from the United States in English, across the 6 categories) and about 21,000 orders from the last 12 months: one weekly delivery from a real directory supplier (same country and equivalent category) and consumption or waste exits (more waste for perishables). They are simulated in chronological order: no exit leaves stock negative. They are inserted in a single transaction.
- **Incidents (TinyDB):** 10,000 incidents from the last 12 months across the 15 locations (more in Medellín), with consistent category, origin, title and description. Status depends on age: recent ones are open or in progress; old ones are mostly resolved.
- **Markers and cleanup:** ingredients have the SKU `VOL-…` (their orders are deleted through it) and each incident is recorded in `incident_seed_log` with a `VOL-…` `source_id` (the historical CSV uses `BRS-…`). `--clear` deletes only that.
- **Idempotent and deterministic:** fixed random seed; if `VOL-` data already exists, it inserts nothing.
- **Seed convention:** locations 1–9 are in Colombia and 10–14 in the United States (9 and 5 locations, as in the incident manager). Inventory does not yet associate locations with countries.
- **Orders** carry the `user_uuid` of the first active admin, like `seed-inventory`.

Tests (10, with temporary SQLite and TinyDB; they do not touch Supabase):

```bash
uv run --project services/brasaland-api python -m unittest scripts/test_seed_volume.py
```

## `nightly_export.py`

From the repository root, with the [`services/jobs`](../services/jobs/README.md) environment and its `.env` (`JOBS_DATABASE_URL`, the `nightly_jobs` role's connection string):

```bash
uv run --project services/jobs python scripts/nightly_export.py                         # yesterday in UTC
TARGET_DATE=2026-11-20 uv run --project services/jobs python scripts/nightly_export.py  # another date
```

On every execution:

1. **Target date:** `TARGET_DATE` (`YYYY-MM-DD`) or, without it, yesterday in UTC (`datetime.now(timezone.utc).date() - timedelta(days=1)`). Only finished days are accepted: the CSV of a day in progress would be incomplete and never exported again.
2. **State:** `run_job` from `services/jobs` closes abandoned executions, skips the date if it already has a `completed` execution (duplicate skip), silently aborts if another instance is `processing` (the lock) and moves the row from `pending` to `processing` before starting.
3. **CSV:** the day's `telemetry_events` rows (00:00 to 00:00 UTC, in order) to `data/raw/telemetry_exports/telemetry_YYYY-MM-DD.csv`, **only if the file does not exist**. Columns `id`, `timestamp` (UTC), `service`, `event_type`, `level`, `value`, `message` and `tags` (JSON). It is written to a temporary file and renamed at the end, so no half-written CSV is left behind. It is a backup: the pipeline reads from the database, not from this file.
4. **Pipeline:** `python data/pipelines/pipeline.py --week-from … --week-to … --trigger scheduled`, with the same interpreter, over the 4 ISO weeks closed as of `target_date + 1` (without `TARGET_DATE`, the pipeline's default run). The result is read from the exit code, with a time limit (`NIGHTLY_PIPELINE_TIMEOUT_MINUTES`, 90 by default).
5. **Closing:** `completed` if all went well; `failed` with the message on any exception. `SIGTERM` also goes through the `finally`.

- **Exit codes:** 0 if it finished, was skipped as a duplicate or was cancelled by the lock; 1 if it failed; 2 if the configuration is invalid (no row is created).
- **Logs:** to `stderr`, one line per event with a UTC timestamp, level, job and status (`INFO` for start, end, skip and cancellation; `ERROR` with the traceback for failures). The pipeline's output is interleaved.
- **Optional** (in `services/jobs/.env`): `NIGHTLY_STALE_MINUTES` (120), `NIGHTLY_PIPELINE_TIMEOUT_MINUTES` (90, lower than the former), `NIGHTLY_PIPELINE_ENVIRONMENT` (the pipeline's `--environment`; locally, `development`) and `PREFECT_API_URL` (without it, each execution starts a temporary Prefect server).
- **Trigger:** the `nightly-scheduler` service in `docker-compose.yml` runs the script with supercronic according to [`nightly_export.crontab`](./nightly_export.crontab): `0 8 * * *` in UTC (03:00 in Bogotá).

Tests (31, with a temporary SQLite and a simulated pipeline; they do not touch Supabase):

```bash
uv run --project services/jobs python -m unittest scripts/test_nightly_export.py
```
