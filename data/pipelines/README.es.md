# Carpeta `data/pipelines`

Esta carpeta agrupa **todos los pipelines de datos del monorepo** relacionados con la compañía: procesos de ingesta, ETL/ELT, limpieza, transformación y carga hacia sistemas analíticos o de producción.

Cada subcarpeta o archivo dentro de `data/pipelines/` debe representar **un pipeline o conjunto de jobs** (por ejemplo `sales-etl`, `telemetry-stream`, `customer-segmentation`) e incluir la configuración necesaria (scripts, orquestación, conectores, esquemas, etc.).

- **Propósito principal**: unificar en un único lugar la lógica de movimiento y transformación de datos que soporta las aplicaciones y analíticas de la compañía.
- **Recomendación**: documenta aquí los pipelines que vayas añadiendo, describiendo su objetivo, orígenes/destinos de datos, dependencias y cómo ejecutarlos en desarrollo, pruebas y producción.

## Pipelines

### Desempeño semanal por local (`weekly_location_performance`)

- **Estado:** en producción (Parte 3): el flow principal coordina tres subflows (extracción, transformación con una task por KPI y carga) y dos opcionales; los KPIs se ven en el dashboard [`/reporte-semanal`](../../uis/backoffice/README.es.md#herramientas) del backoffice. Diseño, ajustes de cada parte y verificación en [`PIPELINE_DESIGN.md`](./PIPELINE_DESIGN.md).
- **Objetivo:** producir el "Reporte Semanal de Costo y Merma por Local" para la dirección: costo de compra, costo de merma, ratio de merma, quiebres de stock y alertas de precio por local y semana ISO.
- **Origen:** `telemetry_events` (solo lectura, solo `production`) y `locations`, en Supabase.
- **Destino:** `reporting.weekly_location_performance` (una fila por local y semana, con upsert) y el log de corridas `reporting.pipeline_runs`.
- **Orquestación:** el flow `weekly_location_performance_flow` de [`pipeline.py`](./pipeline.py) recalcula las 4 últimas semanas cerradas cada noche, lanzado por el script nocturno [`scripts/nightly_export.py`](../../scripts/nightly_export.py) con `--trigger scheduled` (ticket #DEV-53; diseño, §13); backfill por rango desde la CLI o `POST /reporting/pipeline-runs`.
- **Dependencias:** las transformaciones de Pandas, en `data/process/`; los endpoints de `services/reporting/` importan las lecturas y el disparo de este paquete, nunca al revés.
- **Divergencias con el briefing:** [diseño](../../docs/BRIEFING_DIVERGENCES.md#pipeline-de-desempeño-de-negocio) e [implementación](../../docs/BRIEFING_DIVERGENCES.md#pipeline-de-desempeño-de-negocio-resiliente) y [producción](../../docs/BRIEFING_DIVERGENCES.md#pipeline-a-producción-subflows-tests-y-dashboard), en `docs/BRIEFING_DIVERGENCES.md`.

#### Cómo ejecutarlo

```bash
cd data/pipelines
uv sync                       # el paquete, data/process, Prefect (grupo orchestration) y pytest
cp .env.example .env          # REPORTING_DATABASE_URL: Session pooler de Supabase con el rol reporting_pipeline
uv run python pipeline.py     # una corrida: las 4 últimas semanas cerradas de production
uv run pytest                 # pruebas: el flow y cada subflow contra SQLite, el disparo y las lecturas
```

Los tests unitarios de las tasks de KPI están en [`tests/pipelines/`](../../tests/pipelines/README.es.md), en la raíz: `python -m pytest tests/pipelines/test_pipeline.py` desde la raíz, con este entorno activado.

- **Requisitos:** la migración [`005_reporting.sql`](../../services/brasaland-api/migrations/005_reporting.sql) ejecutada en Supabase y el login del rol `reporting_pipeline` (instrucciones en su cabecera).
- **Más comandos:** backfill (`--week-from`, `--week-to`), verificación con los eventos del backoffice local (`--environment development --include-current-week`), deployment de las corridas manuales, sin horario (`--serve`), origen de la corrida en `pipeline_runs` (`--trigger`) y bloques de Prefect (`--register-blocks`). Están en la §10 del diseño, con la frecuencia.
- **Señales de silencio:** cada corrida marca en su log las semanas sin ningún evento de telemetría (`weeks_without_telemetry`, probable fallo de captura) y las que tienen telemetría pero ningún evento de negocio (`weeks_without_business_events`). Las semanas anteriores al 19-nov-2026 salen sin telemetría: la captura no existía.
- **Con Docker:** `docker compose up --build` en la raíz levanta `prefect-server` (http://localhost:4200) y `reporting-pipeline`, que sirve el deployment con `data/pipelines/.env`.
- **Servidor de Prefect:** sin `PREFECT_API_URL`, cada comando arranca uno temporal. En Windows, ese servidor escribe errores internos de su SQLite (`UNIQUE constraint failed: task_run_state`) que no afectan a la corrida; con `PREFECT_API_URL=http://localhost:4200/api` no aparecen.
- **Caché:** la transformación y el catálogo de locales se reutilizan durante 1 hora en el mismo proceso (almacenamiento de resultados de Prefect); una corrida desde el host no aprovecha la del contenedor.
- **Archivos de cada corrida:** la extracción en [`data/raw/telemetry_events/`](../raw/README.es.md) y las comprobaciones en [`data/eval/weekly_location_performance/`](../eval/README.es.md), fuera de Git.
