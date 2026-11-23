# Carpeta `tests/pipelines`

Tests unitarios de los pipelines de datos de [`data/pipelines/`](../../data/pipelines/README.es.md). Prueban las tasks de forma aislada: sin base de datos, sin APIs externas y sin servidor de Prefect.

> _Versión en inglés: [README.md](./README.md)._

## `test_pipeline.py`

Tests de las tasks de transformación del pipeline del "Reporte Semanal de Costo y Merma por Local" (subflow `transform_weekly_location_performance` de [`pipeline.py`](../../data/pipelines/pipeline.py)). Cada test llama a la task con `.fn(...)`, la función que ejecuta Prefect, con eventos en memoria que tienen la forma de `telemetry_events`: `id`, `timestamp`, `event_type` y las propiedades del evento en `tags`, con los campos de las métricas obligatorias del briefing de telemetría.

| Qué se prueba | Tests |
|---|---|
| Un test por KPI del briefing ("KPIs a medir") | Costo de compra por local (`compute_total_purchase_cost`), costo de merma por local (`compute_total_waste_cost`), frecuencia de quiebre de stock (`count_stockout_events`), frecuencia de alertas de precio (`count_price_alert_events`) y ratio de merma (`compute_waste_ratio`) |
| Los cinco KPIs calculados a mano | Una semana de Medellín Centro con sus cuentas en el docstring: 850 COP de compra, 106,25 de merma, ratio 0,125, un quiebre y una alerta |
| Comportamiento defensivo | Eventos mal formados (un número que no lo es, un coste nulo, el país de otro local, `tags` vacío) rechazados sin romper la corrida; las tasks de KPI y el ratio fallan con `ValueError` ante datos que no debían llegarles; semanas que no empiezan en lunes |

## Cómo ejecutarlos

La raíz del monorepo no tiene entorno de Python: los tests usan el de `data/pipelines`, que tiene Prefect, Pandas y los paquetes `brasaland-pipelines` y `brasaland-process`. Desde la raíz:

```bash
cd data/pipelines && uv sync && cd ../..     # una vez
source data/pipelines/.venv/bin/activate     # en Windows: data\pipelines\.venv\Scripts\activate
python -m pytest tests/pipelines/test_pipeline.py
```

O sin activar el entorno: `uv run --project data/pipelines python -m pytest tests/pipelines/test_pipeline.py`.

## Otras pruebas del pipeline

- [`data/process/tests/`](../../data/process/): las funciones puras de la transformación, paso a paso.
- [`data/pipelines/tests/`](../../data/pipelines/): integración del flow y de cada subflow contra SQLite (log de corridas, idempotencia, reintentos, caché, pasos opcionales, señales de silencio), el disparo y las lecturas de la API.
