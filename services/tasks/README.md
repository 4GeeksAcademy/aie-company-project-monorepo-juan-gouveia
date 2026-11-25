# `services/tasks` — asynchronous task queue

_[Versión en español](./README.es.md)._

Python package `brasaland-tasks` (imported as `brasaland_tasks`) with Brasaland's Celery application (ticket #DEV-55). Redis is both the broker and the result backend. The API is the producer: it enqueues and answers right away. The worker is the consumer: an independent process, never inside FastAPI.

```
Client → API (producer) → Redis (broker) → Worker (consumer) → Result
```

## Modules

- **[`celery_app.py`](./celery_app.py):** the Celery instance. The connection comes only from `REDIS_URL` (without it, nothing starts). Two queues, `default` and `dead_letter`, each with its own exchange and routing key. Configuration:
  - ACK only after success (`task_acks_late`, `task_reject_on_worker_lost`), one message at a time (`worker_prefetch_multiplier = 1`);
  - a 60 s soft and 90 s hard time limit for every task;
  - a 300 s `visibility_timeout`, longer than the longest retry wait plus the hard limit;
  - JSON only;
  - the `STARTED` state is tracked and results last 24 h;
  - events on, so Flower can show queued, running and finished tasks;
  - the task names (`telemetry.report`, `dead_letters.record`) that the API uses with `send_task`, with `dead_letters.record` routed to the `dead_letter` queue.
- **[`tasks.py`](./tasks.py):** the tasks; only the worker loads them.
  - `telemetry.report`: the technical telemetry report. It takes `start` and `end` (ISO 8601 UTC, already validated by the API) and `requested_by` as kwargs. It retries transient errors only, with `max_retries=3` and waits of 10, 20 and 40 s. Its final failure, after the retries run out or on a permanent error, publishes a message to the `dead_letter` queue from `on_failure`.
  - `dead_letters.record`: consumes the `dead_letter` queue and stores each message in `ops.task_dead_letters` (migration 007) with `INSERT … ON CONFLICT (task_id) DO NOTHING`. If the database does not answer, it retries with no limit, waiting 10 s to 2 min (less than the `visibility_timeout`).
- **[`errors.py`](./errors.py):** which errors are retried. Transient: the database being down, a dropped connection, `statement_timeout`, the soft time limit and the injected transient fault. Everything else is permanent.
- **[`faults.py`](./faults.py):** forced failures for the demo (`TASKS_FAULT_INJECTION`).
- **[`report.py`](./report.py):** the report built from the metrics in `services/telemetry/analysis.py`, shaped `{period, metrics}`.
- **[`dead_letters.py`](./dead_letters.py):** the DLQ message, with references only (never data or the report), and its idempotent INSERT.
- **[`db.py`](./db.py):** the SQLAlchemy engine for the `task_worker` role (`TASKS_DATABASE_URL`, with psycopg2 set explicitly), created the first time a task needs it.
- **[`logs.py`](./logs.py):** one line per state change of each run, from Celery signals. It carries `task_id`, attempt, state and duration, plus the full error and traceback on failures; never the arguments or the result:

  ```
  2026-11-25T08:22:52Z | INFO | telemetry.report | success | task_id=330a… attempt=1 duration_ms=1140 | Terminada
  ```

## Variables

| Variable | Required | Use |
|---|---|---|
| `REDIS_URL` | Yes | Broker and result backend; the same in the API, the worker and Flower. |
| `TASKS_DATABASE_URL` | In the worker | Connection string for the `task_worker` role (Supabase Session pooler). Reads `telemetry_events` and writes the DLQ. The API does not use it. |
| `TASKS_FAULT_INJECTION` | No | `transient` (4 attempts → DLQ `max_retries_exceeded`), `transient:N` (the first N attempts fail) or `permanent` (→ DLQ `non_retryable`). Read when the worker starts. Never in production. |

## Running the worker locally

Redis must be up (`docker compose up -d redis` from the repository root). From this folder:

```bash
uv sync
cp .env.example .env    # REDIS_URL and TASKS_DATABASE_URL
uv run --env-file .env celery -A brasaland_tasks.celery_app worker -Q default,dead_letter --loglevel=INFO
```

On Windows add `--pool=solo`: Celery's default pool (prefork) does not work there. Check that the worker is connected with `uv run --env-file .env celery -A brasaland_tasks.celery_app inspect ping`, and stop it with `Ctrl+C` (warm shutdown: it finishes the running task first).

## Tests

```bash
uv run pytest
```

They connect to neither Redis nor Supabase: creating the Celery application opens no connection, tasks run in eager mode (retries run immediately and the waits are checked in the log) and the DLQ is tested on SQLite.
