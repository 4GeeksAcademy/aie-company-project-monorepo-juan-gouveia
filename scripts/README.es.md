# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## Scripts disponibles

| Script | Qué hace |
|---|---|
| [`incident-report/`](./incident-report/README.es.md) | Valida y resume el CSV de incidentes operativos, y exporta las métricas a `data/process/results.csv` (Python, sin dependencias; las reglas están en `packages/shared`). |
| [`seed_incidents.py`](./seed_incidents.py) | Carga el histórico del CSV de incidentes en el gestor de incidencias de la API: valida cada fila con las reglas de `packages/shared`, la transforma al modelo del gestor (estado, categoría, título, fecha y sede) con origen `customer` e inserta solo las que no se cargaron antes. Necesita el entorno de la API (TinyDB). |

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
- **Errores:** si no puede leer el CSV, o si la base de datos no se puede abrir, no es un JSON válido o no se puede escribir (por ejemplo, con el disco lleno), muestra el motivo y termina con código 1, sin traceback. Una base dañada no se modifica; tras un fallo de escritura, ejecutarlo de nuevo no duplica nada.
- **Resultado con el CSV del briefing:** 100 filas, 96 insertadas y 4 inválidas (`BRS-000044`, `BRS-000049`, `BRS-000079` y `BRS-000086`). Después, `/api/incidents/summary` da `open` 32, `resolved` 50, `discarded` 14 y `customer_complaint` 48, `equipment_failure` 17, `supply_issue` 22, `staff_issue` 9, los valores esperados del briefing.

Pruebas (20):

```bash
uv run --project services/brasaland-api python -m unittest scripts/test_seed_incidents.py
```
