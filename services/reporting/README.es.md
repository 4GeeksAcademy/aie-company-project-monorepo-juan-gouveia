# Reportes de negocio (`services/reporting`)

Endpoints del **Reporte Semanal de Costo y Merma por Local**, el resultado del pipeline de [`data/pipelines`](../../data/pipelines/README.es.md) ([diseño](../../data/pipelines/PIPELINE_DESIGN.md), §6). Separados del reporte técnico de ingeniería (`services/telemetry`, `GET /telemetry/report`).

> _Versión en inglés: [README.md](./README.md)._

## Rutas

Las tres del briefing, literales y fuera de `/api/v1`, como las de telemetría. Siguen las convenciones de la API: token Bearer y errores `{"error": {"code", "message"}}`.

| Ruta | Rol | Qué hace | Importa de `data/pipelines` |
|---|---|---|---|
| `GET /reporting/weekly-location-performance` | `admin`, `manager` | Los KPIs de todos los locales en una semana: el feed del dashboard | `repository.read_weekly_location_performance` |
| `GET /reporting/pipeline-runs/latest` | `admin`, `manager` | Estado y metadata de la última corrida | `repository.read_latest_pipeline_run` |
| `POST /reporting/pipeline-runs` | `admin` | Pide a Prefect una corrida manual y responde 202, sin esperar | `trigger.trigger_pipeline_run` |

### `GET /reporting/weekly-location-performance`

- **Parámetro:** `week_start` opcional (`YYYY-MM-DD`, un lunes). Sin él, la semana calculada más reciente.
- **Respuesta:** la forma del briefing (§6), más `location_name` en cada local. Los importes están en la moneda del local, sin convertir:

  ```json
  {
    "week_start": "2026-11-16",
    "locations": [
      {
        "location_id": "medellin_centro",
        "location_name": "Medellín Centro",
        "country": "CO",
        "total_purchase_cost": 8420000.0,
        "total_waste_cost": 610000.0,
        "waste_ratio": 0.0724,
        "stockout_events_count": 2,
        "price_alert_events_count": 1,
        "currency": "COP"
      }
    ]
  }
  ```

- **Caché:** 5 minutos por semana (`X-Cache: HIT` o `MISS`). La corrida escribe en otro proceso, así que el dato nuevo puede tardar hasta 5 minutos en verse.
- **Errores:** 422 `invalid_week_start` (no es lunes); 404 `week_not_computed`; 503 `reporting_unavailable` (la base no responde o falta la migración 005).

### `GET /reporting/pipeline-runs/latest`

La última fila de `reporting.pipeline_runs`: `id`, `trigger`, `status` (`pending`, `running`, `completed`, `failed`), `week_from`, `week_to`, `created_at`, `started_at`, `finished_at`, `events_read`, `events_rejected`, `events_discarded`, `waste_events_without_cost`, `issues`, `rows_written`, `failed_task` y `error_message`. Sin caché. 404 `no_pipeline_runs` si nunca corrió.

### `POST /reporting/pipeline-runs`

- **Cuerpo opcional:** `{"week_from": "2026-09-07", "week_to": "2026-11-16"}`. Sin cuerpo, las 4 últimas semanas cerradas.
- **Qué hace:** registra la corrida en `pending` y crea un flow run del deployment `weekly-location-performance/weekly` en el servidor de Prefect (`PREFECT_API_URL`). Lo ejecuta el servicio `reporting-pipeline` (`pipeline.py --serve`). **La API nunca ejecuta el ETL.**
- **Respuesta 202:** la corrida en `pending`. Se sigue con `GET /reporting/pipeline-runs/latest`.
- **Errores:** 422 `invalid_week_range`; 409 `pipeline_run_in_progress`; 503 `orchestrator_unavailable` (sin `PREFECT_API_URL`, servidor caído o deployment sin servir; si la corrida ya estaba registrada, queda en `failed`).

## Cómo está hecho

- **Solo HTTP.** `router.py` autentica, valida y serializa; `schemas.py` tiene los modelos de respuesta y de entrada. La lectura de `reporting.*` y el disparo están en `data/pipelines`, el paquete dueño de esas tablas.
- **Sin Prefect.** La API no importa Prefect: al importarse, Prefect reconfigura el logging del proceso (el logger raíz y el de uvicorn). `trigger.py` habla con la API REST de Prefect con httpx, y `brasaland-pipelines` no declara Prefect como dependencia del paquete (está en su grupo `orchestration`). Una prueba lo vigila.
- **Paquete local** `brasaland-reporting` (se importa como `brasaland_reporting`), instalado en la API en modo editable y montado en `app/main.py`. Solo funciona dentro de la API: usa su `ApiError`, su autenticación, su base y su `TTLCache`.
- **Pruebas:** `tests/reporting/` en la API (`uv run pytest tests/reporting`).
