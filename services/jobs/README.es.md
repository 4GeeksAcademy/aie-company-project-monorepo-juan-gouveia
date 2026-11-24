# `services/jobs` — control de estado de los jobs programados

_[English version](./README.md)._

Paquete Python `brasaland-jobs` (se importa como `brasaland_jobs`) con la lógica de estado del script nocturno de telemetría ([`scripts/nightly_export.py`](../../scripts/README.es.md#nightly_exportpy), ticket #DEV-53). Registra cada ejecución en la tabla `ops.job_runs` de Supabase ([migración 006](../brasaland-api/migrations/006_job_runs.sql)). No es un servicio que se ejecute solo y no depende de la API ni de FastAPI: el script es un proceso independiente.

## La máquina de estados

```
pending → processing → completed
                    ↘ failed
```

| Estado | Cuándo |
| --- | --- |
| `pending` | Se crea la fila, antes de empezar |
| `processing` | Antes de hacer ningún trabajo. **Es el lock** |
| `completed` | Solo si todo terminó bien |
| `failed` | Ante cualquier excepción, con el mensaje en `error_message` |

- **Lock:** el propio estado `processing`, sin tabla ni columna aparte. El índice único parcial `uq_job_runs_one_processing` admite una sola fila `processing` por job, así que, aunque dos instancias arranquen en el mismo instante, la segunda transición falla de forma atómica y esa instancia aborta.
- **Idempotencia:** por `(job_name, target_date)`. Si ya hay una ejecución `completed` para la fecha, no se repite.
- **Omisión y cancelación:** la omisión por duplicado y la cancelación por lock solo van al log (`INFO`), sin fila nueva: ejecutar dos veces deja `job_runs` igual que una vez. La instancia que pierde la carrera del índice ya había creado su fila `pending`; la cierra como `failed` con `lock_held: …`.
- **Ninguna fila zombi:** un `try/except/finally` pasa la fila a `failed` ante cualquier excepción, también `KeyboardInterrupt` y `SystemExit` (el script convierte `SIGTERM` en `SystemExit`). Un `SIGKILL` no pasa por el `finally`: la siguiente ejecución cierra como `failed` (`abandoned: …`) las filas abiertas con más de `NIGHTLY_STALE_MINUTES` (120 por defecto).
- **`job_runs` no es `reporting.pipeline_runs`:** `job_runs` registra la orquestación (export, disparo del pipeline, lock e idempotencia); el pipeline sigue registrando su ETL en `pipeline_runs`.

## Módulos

- **[`job_runner.py`](./job_runner.py):** la tabla `ops.job_runs` (como en la 006), las consultas `has_processing_lock`, `has_completed_for_date`, `get_run` y `list_runs`, las transiciones `create_run`, `start_run` (lanza `LockHeld` si otra instancia tiene el lock), `complete_run` y `fail_run`, `abandon_stale_runs` y `run_job`, que ejecuta un trabajo con la máquina de estados completa y devuelve `completed`, `skipped` o `cancelled` (un fallo se propaga).
- **[`logs.py`](./logs.py):** formato de log de los jobs, con timestamp en UTC, nivel, nombre del job y estado resultante en cada línea:

```
2026-11-24T12:12:15Z | INFO | nightly_export | processing | target_date=2026-11-23 | Inicio de la ejecución a337f563-…
```

## Entorno

```bash
cd services/jobs
uv sync               # el paquete, el grupo script (pipeline, Prefect 3.9.4 y python-dotenv) y pytest
uv run pytest         # 29 pruebas, con SQLite (sin Supabase)
```

- **Grupo `script`:** el entorno del script nocturno. Incluye `brasaland-pipelines` (de `data/pipelines`, en modo editable) porque el script calcula las semanas con `compute_weeks` y lanza el pipeline como subproceso con este mismo intérprete. Quien instala solo el paquete recibe únicamente SQLAlchemy y psycopg2.
- **Configuración:** `.env` en esta carpeta (no se versiona), a partir de [`.env.example`](./.env.example). La única obligatoria es `JOBS_DATABASE_URL`, la cadena del rol `nightly_jobs`. Cómo crear el rol y su login: [README de la API, "Esquema `ops`"](../brasaland-api/README.es.md#esquema-ops-script-nocturno-de-telemetría).
- **Docker:** [`Dockerfile`](./Dockerfile) es la imagen del servicio `nightly-scheduler` (supercronic con el crontab del script); se construye desde el `docker-compose.yml` de la raíz.
