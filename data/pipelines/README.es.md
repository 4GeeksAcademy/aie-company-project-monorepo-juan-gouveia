# Carpeta `data/pipelines`

Esta carpeta agrupa **todos los pipelines de datos del monorepo** relacionados con la compañía: procesos de ingesta, ETL/ELT, limpieza, transformación y carga hacia sistemas analíticos o de producción.

Cada subcarpeta o archivo dentro de `data/pipelines/` debe representar **un pipeline o conjunto de jobs** (por ejemplo `sales-etl`, `telemetry-stream`, `customer-segmentation`) e incluir la configuración necesaria (scripts, orquestación, conectores, esquemas, etc.).

- **Propósito principal**: unificar en un único lugar la lógica de movimiento y transformación de datos que soporta las aplicaciones y analíticas de la compañía.
- **Recomendación**: documenta aquí los pipelines que vayas añadiendo, describiendo su objetivo, orígenes/destinos de datos, dependencias y cómo ejecutarlos en desarrollo, pruebas y producción.

## Pipelines

### Desempeño semanal por local (`weekly_location_performance`)

- **Estado:** diseñado ([`PIPELINE_DESIGN.md`](./PIPELINE_DESIGN.md)); la implementación con Prefect llega en las Partes 2 y 3.
- **Objetivo:** producir el "Reporte Semanal de Costo y Merma por Local" para la dirección: costo de compra, costo de merma, ratio de merma, quiebres de stock y alertas de precio por local y semana ISO.
- **Origen:** `telemetry_events` (solo lectura, solo `production`) y `locations`, en Supabase.
- **Destino:** `reporting.weekly_location_performance` (una fila por local y semana, con upsert) y el log de corridas `reporting.pipeline_runs`.
- **Orquestación:** un flow de Prefect, los lunes a las 06:00 America/Bogota, que recalcula las 4 últimas semanas cerradas; backfill por rango desde `POST /reporting/pipeline-runs`.
- **Dependencias:** las transformaciones de Pandas, en `data/process/`; los endpoints de `services/reporting/` importan las lecturas y el disparo de este paquete, nunca al revés.
- **Divergencias con el briefing:** [`docs/BRIEFING_DIVERGENCES.md`](../../docs/BRIEFING_DIVERGENCES.md#pipeline-de-desempeño-de-negocio).
