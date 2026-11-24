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
  - events on, so Flower can show queued, running and finished tasks.

## Running the worker locally

Redis must be up (`docker compose up -d redis` from the repository root). From this folder:

```bash
uv sync
cp .env.example .env    # REDIS_URL=redis://127.0.0.1:6379/0
uv run --env-file .env celery -A brasaland_tasks.celery_app worker -Q default,dead_letter --loglevel=INFO
```

On Windows add `--pool=solo`: Celery's default pool (prefork) does not work there. Check that the worker is connected with `uv run --env-file .env celery -A brasaland_tasks.celery_app inspect ping`, and stop it with `Ctrl+C` (warm shutdown: it finishes the running task first).

## Tests

```bash
uv run pytest
```

They do not connect to Redis: creating the Celery application opens no connection.
