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
  - eventos activados, para que Flower muestre las tareas en cola, en proceso y terminadas.

## Arrancar el worker en local

Redis debe estar levantado (`docker compose up -d redis` desde la raíz del repositorio). Desde esta carpeta:

```bash
uv sync
cp .env.example .env    # REDIS_URL=redis://127.0.0.1:6379/0
uv run --env-file .env celery -A brasaland_tasks.celery_app worker -Q default,dead_letter --loglevel=INFO
```

En Windows, añade `--pool=solo`: el pool por defecto de Celery (prefork) no funciona ahí. Comprueba que el worker está conectado con `uv run --env-file .env celery -A brasaland_tasks.celery_app inspect ping` y detenlo con `Ctrl+C` (parada ordenada: antes termina la tarea en curso).

## Pruebas

```bash
uv run pytest
```

No se conectan a Redis: crear la aplicación de Celery no abre ninguna conexión.
