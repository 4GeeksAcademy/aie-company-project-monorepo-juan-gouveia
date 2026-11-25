# `services/tasks` — cola de tareas asíncronas

_[English version](./README.md)._

Paquete Python `brasaland-tasks` (se importa como `brasaland_tasks`) con la aplicación Celery de Brasaland (ticket #DEV-55). Redis es a la vez el broker y el backend de resultados. La API es el productor: encola y responde al momento. El worker es el consumidor: un proceso independiente, nunca dentro de FastAPI.

```
Cliente → API (productor) → Redis (broker) → Worker (consumidor) → Resultado
```

## Módulos

- **[`celery_app.py`](./celery_app.py):** la instancia de Celery. La conexión sale solo de `REDIS_URL` (sin ella, nada arranca). Dos colas, `default` y `dead_letter`, cada una con su propio exchange y su propia routing key. Configuración:
  - ACK solo tras éxito (`task_acks_late`, `task_reject_on_worker_lost`) y mensajes de uno en uno (`worker_prefetch_multiplier = 1`);
  - límite de 60 s (suave) y 90 s (duro) para toda tarea;
  - `visibility_timeout` de 300 s, mayor que la espera de reintento más larga sumada al límite duro;
  - solo JSON;
  - se registra el estado `STARTED` y los resultados duran 24 h;
  - eventos activados, para que Flower muestre las tareas en cola, en proceso y terminadas;
  - `dead_letters.record` enrutada a la cola `dead_letter`.
- **[`names.py`](./names.py):** las colas, los nombres de las tareas (`telemetry.report`, `dead_letters.record`) y la duración de los resultados, sin efectos al importar. La API los usa sin `REDIS_URL` (encola con `send_task` por nombre); `celery_app` los reexporta.
- **[`tasks.py`](./tasks.py):** las tareas; solo las carga el worker.
  - `telemetry.report`: el informe técnico de telemetría. Recibe en kwargs `start` y `end` (ISO 8601 UTC, ya validados por la API) y `requested_by`. Reintenta solo los errores transitorios, con `max_retries=3` y esperas de 10, 20 y 40 s. Su fallo final, al agotar los reintentos o por un error permanente, publica un mensaje en la cola `dead_letter` desde `on_failure`.
  - `dead_letters.record`: consume la cola `dead_letter` y guarda cada mensaje en `ops.task_dead_letters` (migración 007) con `INSERT … ON CONFLICT (task_id) DO NOTHING`. Si la base no responde, reintenta sin límite, con esperas de 10 s a 2 min (menos que el `visibility_timeout`).
- **[`errors.py`](./errors.py):** qué errores se reintentan. Transitorios: la base caída, la conexión cortada, `statement_timeout`, el límite suave y el fallo transitorio inyectado. El resto es permanente.
- **[`faults.py`](./faults.py):** fallos forzados para la demo (`TASKS_FAULT_INJECTION`).
- **[`report.py`](./report.py):** el informe con las métricas de `services/telemetry/analysis.py`, con la forma `{period, metrics}`.
- **[`dead_letters.py`](./dead_letters.py):** el mensaje de la DLQ, solo con referencias (nunca datos ni el informe), y su INSERT idempotente.
- **[`db.py`](./db.py):** el motor de SQLAlchemy del rol `task_worker` (`TASKS_DATABASE_URL`, con psycopg2 explícito), creado la primera vez que una tarea lo pide.
- **[`logs.py`](./logs.py):** una línea por cambio de estado de cada ejecución, a partir de las señales de Celery. Lleva `task_id`, intento, estado y duración, y el error completo con su traceback en los fallos; nunca los argumentos ni el resultado:

  ```
  2026-11-25T08:22:52Z | INFO | telemetry.report | success | task_id=330a… attempt=1 duration_ms=1140 | Terminada
  ```

## Variables

| Variable | Obligatoria | Uso |
|---|---|---|
| `REDIS_URL` | Sí | Broker y backend de resultados; la misma en la API, el worker y Flower. |
| `TASKS_DATABASE_URL` | En el worker | Cadena del rol `task_worker` (Session pooler de Supabase). Lee `telemetry_events` y escribe la DLQ. La API no la usa. |
| `TASKS_FAULT_INJECTION` | No | `transient` (4 intentos → DLQ `max_retries_exceeded`), `transient:N` (fallan los N primeros intentos) o `permanent` (→ DLQ `non_retryable`). Se lee al arrancar el worker. Nunca en producción. |

## Arrancar el worker en local

Redis debe estar levantado (`docker compose up -d redis` desde la raíz del repositorio). Desde esta carpeta:

```bash
uv sync
cp .env.example .env    # REDIS_URL y TASKS_DATABASE_URL
uv run --env-file .env celery -A brasaland_tasks.celery_app worker -Q default,dead_letter --loglevel=INFO
```

En Windows, añade `--pool=solo`: el pool por defecto de Celery (prefork) no funciona ahí. Comprueba que el worker está conectado con `uv run --env-file .env celery -A brasaland_tasks.celery_app inspect ping` y detenlo con `Ctrl+C` (parada ordenada: antes termina la tarea en curso).

## Pruebas

```bash
uv run pytest
```

No se conectan a Redis ni a Supabase: crear la aplicación de Celery no abre ninguna conexión, las tareas corren en modo eager (los reintentos se ejecutan en el momento y las esperas se comprueban en el log) y la DLQ se prueba en SQLite.
