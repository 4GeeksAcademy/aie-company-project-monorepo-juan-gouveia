# Carpeta `data/process`

Esta carpeta contiene **datos procesados/intermedios** y/o artefactos derivados de los pipelines (por ejemplo: datasets limpios, features, agregados, tablas intermedias o resultados de transformaciones).

- **Propósito principal**: separar claramente los datos “raw” de los datos listos para análisis/modelado/consumo por apps.
- **Recomendación**: documenta qué pipeline genera cada artefacto, su esquema, periodicidad, y cómo se valida su calidad (checks, constraints, tests de datos).

## Artefactos

### `results.csv`

- **Lo genera:** [`scripts/incident-report/analyze.py`](../../scripts/incident-report/README.es.md), cuando se responde que sí a la pregunta de exportación.
- **Esquema:** una fila por métrica, con las columnas `metric`, `value` y `percentage`. La lista de métricas está en el README del script.
- **Periodicidad:** cada ejecución sobrescribe el archivo anterior.
- **Calidad:** las pruebas del script (`python -m unittest`) comprueban los valores con el dataset de `data/raw/`.
- **Versionado:** no se sube a Git (está en `.gitignore`), porque se regenera en cada ejecución.

## Transformaciones reutilizables (`brasaland-process`)

Esta carpeta es también un paquete local de Python, `brasaland-process` (se importa como `brasaland_process`), con las transformaciones de los pipelines de [`data/pipelines/`](../pipelines/README.es.md). Son funciones puras de Pandas: no leen ni escriben en la base y no usan bucles sobre filas. Los pipelines lo instalan en modo editable con uv.

### `weekly_location_performance.py`

Transformación del "Reporte Semanal de Costo y Merma por Local" ([diseño, §3.3](../pipelines/PIPELINE_DESIGN.md#33-reglas-de-la-transformación)). `build_weekly_location_performance(events, locations, weeks)` recibe los eventos extraídos de `telemetry_events`, el catálogo `locations` y los lunes de las semanas de la corrida, y devuelve:

- **`rows`:** una fila por local y semana (14 × semanas, con ceros donde no hubo actividad) con las columnas de `reporting.weekly_location_performance`: `location_id` (el `code` del local), `country`, `week_start`, `total_purchase_cost`, `total_waste_cost`, `waste_ratio`, `stockout_events_count`, `price_alert_events_count` y `currency`.
- **Los conteos del log de la corrida:** `events_read`, `events_rejected`, `events_discarded`, `waste_events_without_cost` e `issues` (motivo → número de eventos). Siempre cuadran: leídos = usados + rechazados + descartados.

| Paso | Función | Regla |
|---|---|---|
| Refinar | `refine_events` | Una columna por cada propiedad de negocio de `tags`, con su tipo; nunca `user_id`, `session_id` ni `request_id` |
| Validar | `validate_events` | Rechaza el local fuera del catálogo (`unknown_location`), el país o la moneda que no son los del local (`country_mismatch`, `currency_mismatch`) y los datos imprescindibles ausentes o inválidos (`invalid_payload`) |
| Deduplicar | `deduplicate_facts` | Un mismo hecho con otro `eventId` cuenta una vez: clave `(event_type, order_id)`, o `trigger_order_id` en los quiebres (`duplicate_fact`) |
| Alertas | `keep_price_increases` | Solo las subidas, `variance_pct > 0` (`price_decrease`) |
| Semana | `week_start_of` | Lunes de la semana ISO, en UTC; fuera de las semanas de la corrida se descarta (`outside_window`) |
| Costo de compra por local | `compute_total_purchase_cost` | Σ `quantity × unit_cost` de las entradas, por local y semana |
| Costo de merma por local | `compute_total_waste_cost` | Σ `quantity × unit_cost` de las mermas; una merma sin `unit_cost` cuenta 0 |
| Frecuencia de quiebre de stock | `count_stockout_events` | Número de `stock_threshold_triggered` |
| Frecuencia de alertas de precio | `count_price_alert_events` | Número de alertas de subida |
| Completar | `assemble_weekly_location_performance` | Los 14 locales en cada semana, con ceros; importes con 2 decimales, sin convertir monedas; `location_id` = `code` del local |
| Ratio de merma | `compute_waste_ratio` | `total_waste_cost / total_purchase_cost` de cada fila, con 4 decimales; 0 sin compras; puede superar 1 |

- **Una función por paso del pipeline.** `prepare_weekly_location_facts` agrupa los cinco primeros pasos (refinar a semana) y devuelve los hechos que cuentan (`WeeklyLocationFacts`) con los conteos del log. Después, una función por KPI del briefing, con el nombre de su columna: son las tasks del subflow de transformación de [`data/pipelines/pipeline.py`](../pipelines/README.es.md). `build_weekly_location_performance` las encadena en el mismo orden.
- **Defensivas.** Un evento mal formado (un número que no lo es, un dato imprescindible nulo, `tags` vacío) se rechaza en la preparación y queda en el log; no rompe la corrida. Las funciones de los KPIs fallan con `ValueError` si reciben un hecho que la preparación debía haber rechazado (una entrada sin coste, una alerta de bajada, un coste negativo): un KPI mal contado en silencio es peor que una corrida fallida.
- **Señales de silencio.** `detect_silent_weeks` clasifica las semanas de la corrida sin ningún evento de telemetría (`weeks_without_telemetry`, probable fallo de captura) y con telemetría pero sin eventos de negocio (`weeks_without_business_events`, semana sin actividad registrada).

**Pruebas:** `cd data/process && uv run pytest`, con datos sintéticos en memoria (nunca en Supabase).
