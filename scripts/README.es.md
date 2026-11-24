# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## Scripts disponibles

| Script | Qué hace |
|---|---|
| [`incident-report/`](./incident-report/README.es.md) | Valida y resume el CSV de incidentes operativos, y exporta las métricas a `data/process/results.csv` (Python, sin dependencias; las reglas están en `packages/shared`). |
| [`seed_incidents.py`](./seed_incidents.py) | Carga el histórico del CSV de incidentes en el gestor de incidencias de la API: valida cada fila con las reglas de `packages/shared`, la transforma al modelo del gestor (estado, categoría, título, fecha y sede) con origen `customer` e inserta solo las que no se cargaron antes. Necesita el entorno de la API (TinyDB). |
| [`seed_volume.py`](./seed_volume.py) | Carga volumen realista para medir el rendimiento de la API (tarea de caching): 150 ingredientes y unas 21 000 órdenes en Supabase, y 10 000 incidencias en TinyDB. Todo va marcado (`VOL-`) y `--clear` lo retira sin tocar los datos reales. Necesita el entorno de la API y su `.env`. |
| [`nightly_export.py`](./nightly_export.py) | Script nocturno de telemetría (ticket #DEV-53): exporta a CSV los `telemetry_events` del día anterior (en UTC) a `data/raw/telemetry_exports/`, lanza el pipeline de desempeño de negocio como subproceso y registra cada ejecución en `ops.job_runs`, con lock e idempotencia por fecha. Lo dispara cada noche el servicio `nightly-scheduler` (crontab en [`nightly_export.crontab`](./nightly_export.crontab)). Necesita el entorno de `services/jobs` y su `.env`. |

## `seed_incidents.py`

Desde la raíz del repositorio:

```bash
uv run --project services/brasaland-api python scripts/seed_incidents.py            # data/raw/incidents-brasaland.csv
uv run --project services/brasaland-api python scripts/seed_incidents.py otra.csv   # otro archivo
```

- **Dónde escribe:** en el archivo TinyDB de la API (`services/brasaland-api/storage/brasaland-db.json`), o en `BRASALAND_DB_PATH` si está definida. Se puede ejecutar con la API arrancada.
- **Transformaciones (briefing del gestor):** `OPEN`/`CLOSED`/`DISCARDED` → `open`/`resolved`/`discarded`; las categorías del CSV a las del gestor (`FOOD_QUALITY` → `customer_complaint`); `title` son los primeros 120 caracteres de `description`; `date` es la medianoche UTC de `created_at` y `updated_at`; `location_id` → `branch` (`COL-10` y las sedes sin mapeo → `central`); `origin` siempre `customer`.
- **Inválidos:** las filas que incumplen alguna regla del analizador (o que no se pueden transformar) no se insertan y se listan al final con su fila y su motivo.
- **Idempotente:** guarda el `incident_id` de cada fila cargada en la tabla `incident_seed_log` (no en la incidencia). Una segunda ejecución inserta 0 y las cuenta como "ya cargadas".
- **Errores:** si no puede leer el CSV, o si la base de datos no se puede abrir, no es un JSON válido o no se puede escribir (por ejemplo, con el disco lleno), muestra el motivo y termina con código 1, sin traceback. Una base dañada no se modifica; tras un fallo de escritura, ejecutarlo de nuevo no duplica nada. El reporte final muestra la ruta absoluta de la base de datos a propósito, para que quien lo ejecuta confirme qué archivo se modificó (`BRASALAND_DB_PATH` puede apuntar a cualquier sitio).
- **Resultado con el CSV del briefing:** 100 filas, 96 insertadas y 4 inválidas (`BRS-000044`, `BRS-000049`, `BRS-000079` y `BRS-000086`). Después, `/api/incidents/summary` da `open` 32, `resolved` 50, `discarded` 14 y `customer_complaint` 48, `equipment_failure` 17, `supply_issue` 22, `staff_issue` 9, los valores esperados del briefing.

Pruebas (20):

```bash
uv run --project services/brasaland-api python -m unittest scripts/test_seed_incidents.py
```

## `seed_volume.py`

Desde la raíz del repositorio, **con la API parada** (escribe en bloque en `brasaland-db.json`):

```bash
uv run --project services/brasaland-api --env-file services/brasaland-api/.env python scripts/seed_volume.py          # carga
uv run --project services/brasaland-api --env-file services/brasaland-api/.env python scripts/seed_volume.py --clear  # retira
```

- **Inventario (Supabase):** 150 ingredientes (75 de Colombia con nombre en español y 75 de Estados Unidos en inglés, en las 6 categorías) y unas 21 000 órdenes de los últimos 12 meses: una entrega semanal de un proveedor real del directorio (mismo país y categoría equivalente) y salidas de consumo o merma (más merma en lo perecedero). Se simulan en orden cronológico: ninguna salida deja el stock en negativo. Se insertan en una sola transacción.
- **Incidencias (TinyDB):** 10 000 incidencias de los últimos 12 meses en las 15 sedes (más en Medellín), con categoría, origen, título y descripción coherentes. El estado depende de la antigüedad: las recientes, abiertas o en curso; las antiguas, casi todas resueltas.
- **Marcas y limpieza:** los ingredientes llevan el SKU `VOL-…` (sus órdenes se borran a través de él) y cada incidencia queda anotada en `incident_seed_log` con un `source_id` `VOL-…` (el CSV histórico usa `BRS-…`). `--clear` borra solo eso.
- **Idempotente y determinista:** semilla aleatoria fija; si ya hay datos `VOL-`, no inserta nada.
- **Convención de la semilla:** los locales 1–9 son de Colombia y los 10–14 de Estados Unidos (9 y 5 sedes, como en el gestor). El inventario todavía no asocia locales a países.
- **Las órdenes** llevan el `user_uuid` del primer administrador activo, como `seed-inventory`.

Pruebas (10, con SQLite y TinyDB temporales; no tocan Supabase):

```bash
uv run --project services/brasaland-api python -m unittest scripts/test_seed_volume.py
```

## `nightly_export.py`

Desde la raíz del repositorio, con el entorno de [`services/jobs`](../services/jobs/README.es.md) y su `.env` (`JOBS_DATABASE_URL`, la cadena del rol `nightly_jobs`):

```bash
uv run --project services/jobs python scripts/nightly_export.py                         # ayer en UTC
TARGET_DATE=2026-11-20 uv run --project services/jobs python scripts/nightly_export.py  # otra fecha
```

En cada ejecución:

1. **Fecha objetivo:** `TARGET_DATE` (`YYYY-MM-DD`) o, sin ella, ayer en UTC (`datetime.now(timezone.utc).date() - timedelta(days=1)`). Solo se admiten días ya terminados: el CSV de un día a medias quedaría incompleto y no se volvería a exportar.
2. **Estado:** `run_job` de `services/jobs` cierra las ejecuciones abandonadas, omite la fecha si ya tiene una ejecución `completed` (omisión por duplicado), aborta en silencio si otra instancia está en `processing` (el lock) y pasa la fila de `pending` a `processing` antes de empezar.
3. **CSV:** las filas de `telemetry_events` del día (de 00:00 a 00:00 UTC, en orden) a `data/raw/telemetry_exports/telemetry_YYYY-MM-DD.csv`, **solo si el archivo no existe**. Columnas `id`, `timestamp` (UTC), `service`, `event_type`, `level`, `value`, `message` y `tags` (JSON). Se escribe en un temporal y se renombra al final, para no dejar un CSV a medias. Es una copia de seguridad: el pipeline lee de la base, no de este archivo.
4. **Pipeline:** `python data/pipelines/pipeline.py --week-from … --week-to … --trigger scheduled`, con el mismo intérprete, sobre las 4 semanas ISO cerradas a fecha de `target_date + 1` (sin `TARGET_DATE`, la corrida por defecto del pipeline). El resultado se lee del código de salida, con un tiempo máximo (`NIGHTLY_PIPELINE_TIMEOUT_MINUTES`, 90 por defecto).
5. **Cierre:** `completed` si todo fue bien; `failed` con el mensaje ante cualquier excepción. `SIGTERM` también pasa por el `finally`.

- **Códigos de salida:** 0 si terminó, se omitió por duplicado o se canceló por lock; 1 si falló; 2 si la configuración no es válida (sin crear ninguna fila).
- **Logs:** a `stderr`, una línea por evento con timestamp UTC, nivel, job y estado (`INFO` para inicio, fin, omisión y cancelación; `ERROR` con la traza para los fallos). La salida del pipeline va intercalada.
- **Opcionales** (en `services/jobs/.env`): `NIGHTLY_STALE_MINUTES` (120), `NIGHTLY_PIPELINE_TIMEOUT_MINUTES` (90, menor que el anterior), `NIGHTLY_PIPELINE_ENVIRONMENT` (el `--environment` del pipeline; en local, `development`) y `PREFECT_API_URL` (sin ella, cada ejecución arranca un servidor temporal de Prefect).
- **Disparador:** el servicio `nightly-scheduler` de `docker-compose.yml` ejecuta el script con supercronic según [`nightly_export.crontab`](./nightly_export.crontab): `0 8 * * *` en UTC (03:00 en Bogotá).

Pruebas (31, con SQLite temporal y el pipeline simulado; no tocan Supabase):

```bash
uv run --project services/jobs python -m unittest scripts/test_nightly_export.py
```
