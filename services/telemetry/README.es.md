# Análisis de telemetría (`services/telemetry`)

Pipeline de análisis del **reporte técnico** de telemetría: métricas operacionales calculadas con Pandas sobre la tabla `telemetry_events` de Supabase. Es un radar para el equipo de ingeniería (volumen, errores, latencia y fallos de autenticación), no un reporte de negocio. El diseño está en el [plan de telemetría, sección 16](../../docs/telemetry/telemetry-plan.md#16-fase-de-reporte-técnico).

> _Versión en inglés: [README.md](./README.md)._

## Métricas (`analysis.py`)

Cada función recibe una conexión de SQLAlchemy y la ventana `[start, end)` en UTC, que decide quien la llama, y devuelve una lista de dicts lista para JSON. Todas agrupan por día UTC.

| Función | Pregunta operacional | Eventos | Fila |
|---|---|---|---|
| `events_per_day` | ¿Cuánto volumen tiene el sistema cada día y qué parte es aviso o error? | Todos | `{date, total, info, warn, error}`; también los días sin eventos, con ceros |
| `error_rate_by_type` | ¿Qué tipos de fallo dominan cada día y qué peso tienen sobre el volumen? | Todos (el total del día es el denominador) | `{date, event_type, level, count, rate}`, solo tipos `warn` o `error` |
| `api_latency_by_route` | ¿Qué rutas de la API responden lento y cuánto? | `api_latency_recorded` | `{date, method, route, samples, avg_ms, max_ms}`; media ponderada por `1/sample_rate` |
| `auth_failure_rate` | ¿Qué proporción de los intentos de login falla cada día? | `login_failed` y `login_succeeded` | `{date, attempts, failed, failure_rate}` |

Las tasas son fracciones de 0 a 1 con 4 decimales, y las fechas van como `YYYY-MM-DD`.

## Cómo calcula cada métrica

Siempre en el mismo orden: **cargar (SQL) → refinar (Pandas) → convertir tipos → agrupar → agregar → servir**.

- **Cargar.** Una sola consulta por métrica, con la ventana (`timestamp >= :start AND timestamp < :end`) y los `event_type` que necesita, solo con las columnas que usa. Nunca carga toda la tabla.
- **Refinar.** Extrae de `tags` las dimensiones (`route`, `method`, `duration_ms`, `sample_rate`) y descarta las filas en las que faltan.
- **Convertir tipos.** `pd.to_datetime(..., utc=True)` antes de agrupar por día: según el driver, `timestamp` llega como texto (SQLite) o como fecha (PostgreSQL).
- **Agrupar y agregar.** `groupby` con `.size()`, `.agg()` y `.sum()`, sin bucles.

Las funciones solo leen la base: dos llamadas con los mismos parámetros devuelven lo mismo.

## Cómo se consume

Es un paquete Python (`brasaland-telemetry`) cuya carpeta es el propio paquete: `services/telemetry/analysis.py` se importa como `brasaland_telemetry.analysis`. Sus dependencias son `pandas` y `sqlalchemy`.

- **API:** lo declara como dependencia local en su `pyproject.toml` (`[tool.uv.sources]`, en modo editable), igual que `packages/shared`, así que `uv sync` lo instala y los cambios se ven sin reinstalar.
- **Docker:** `services/Dockerfile` lo instala en modo editable, y `docker-compose.yml` monta la carpeta. `pandas` llega con `services/requirements.txt`.

## Pruebas

Se prueban desde la API, sobre una tabla `telemetry_events` en SQLite: `services/brasaland-api/tests/telemetry/test_report_analysis.py`. Cubren cada métrica, los límites de la ventana, los días vacíos, la media ponderada, los tipos nativos y la serialización a JSON, que sean repetibles, una sola consulta con ventana por métrica y la ausencia de bucles.

```bash
cd services/brasaland-api
uv run pytest tests/telemetry/test_report_analysis.py
```
