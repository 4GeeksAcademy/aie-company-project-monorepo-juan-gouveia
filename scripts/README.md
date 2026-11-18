# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## Available scripts

| Script | What it does |
|---|---|
| [`incident-report/`](./incident-report/README.md) | Validates and summarizes the operational incidents CSV, and exports the metrics to `data/process/results.csv` (Python, no dependencies; the rules live in `packages/shared`). |
| [`seed_incidents.py`](./seed_incidents.py) | Loads the historical incidents CSV into the API's incident manager: validates each row with the `packages/shared` rules, transforms it to the manager's model (status, category, title, date and location) with origin `customer`, and inserts only the rows that were not loaded before. It needs the API environment (TinyDB). |

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
- **Result with the briefing CSV:** 100 rows, 96 inserted and 4 invalid (`BRS-000044`, `BRS-000049`, `BRS-000079` and `BRS-000086`). Afterwards, `/api/incidents/summary` gives `open` 32, `resolved` 50, `discarded` 14 and `customer_complaint` 48, `equipment_failure` 17, `supply_issue` 22, `staff_issue` 9, the values the briefing expects.

Tests (16):

```bash
uv run --project services/brasaland-api python -m unittest scripts/test_seed_incidents.py
```

> _Spanish version: [README.es.md](./README.es.md)._
