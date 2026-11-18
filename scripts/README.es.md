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
