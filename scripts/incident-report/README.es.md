# Procesador de reportes de incidentes (`scripts/incident-report`)

Script de consola que valida y resume el CSV de incidentes operativos de Brasaland: fallas de equipos, abastecimiento, quejas de clientes, calidad de alimentos y personal. Operaciones lo ejecuta antes de la reunión de la mañana, y sus datos servirán de base al futuro dashboard operativo.

## Requisitos

- Python 3 (probado con 3.12).
- Sin dependencias externas: solo usa la librería estándar (`csv`, `decimal`, `unittest`).

## Dónde está la lógica

Las reglas de validación y el análisis están en el backend, en [`services/brasaland-api/app/domains/incidents/service.py`](../../services/brasaland-api/app/domains/incidents/service.py), que es su fuente de verdad. La API usa ese mismo servicio, así que el script y el backoffice dan siempre los mismos resultados.

El script solo se ocupa de la consola: resolver la ruta, dar formato al reporte, preguntar y exportar. Importa el servicio añadiendo `services/brasaland-api` a la ruta de Python. Como el servicio solo usa la librería estándar, no hace falta instalar nada. Eso sí, el script tiene que ejecutarse dentro del repositorio: si se copia `analyze.py` a otro sitio, no encuentra el servicio.

## Uso

Desde esta carpeta:

```bash
python analyze.py incidents-brasaland.csv
```

Desde la raíz del repositorio:

```bash
python scripts/incident-report/analyze.py data/raw/incidents-brasaland.csv
```

La ruta se interpreta desde la carpeta actual. Si no existe ahí, el script busca el mismo nombre en `data/raw/`. Si no encuentra el archivo, o si al CSV le faltan columnas, muestra un error y termina con código 1.

## Qué hace

1. Lee el CSV (UTF-8, con o sin BOM) y comprueba que tenga las 9 columnas esperadas.
2. Marca como inválido todo registro que incumpla alguna de estas reglas:

   | Regla | Condición |
   |---|---|
   | `missing_location` | `location_id` vacío o fuera de `COL-01`…`COL-10` y `FLA-01`…`FLA-04` |
   | `invalid_category` | `category` vacía o fuera de `CUSTOMER_COMPLAINT`, `EQUIPMENT`, `SUPPLY`, `FOOD_QUALITY` y `STAFF` |
   | `empty_description` | `description` con menos de 5 caracteres |
   | `missing_reporter` | `reporter_id` vacío |
   | `invalid_status` | `status` fuera de `OPEN`, `CLOSED` y `DISCARDED`. Esta regla no está en el briefing: evita que un estado desconocido cuente como válido |
   | `closed_without_score` | `status = CLOSED` sin `satisfaction_score` |
   | `score_out_of_range` | Hay puntaje, pero no es un entero entre 1 y 5 |

   Un registro que incumple varias reglas suma en cada una, pero cuenta una sola vez en el total de inválidos.
3. Sobre los registros válidos, calcula el total por categoría y por estado, con su porcentaje, y el índice de satisfacción de los casos cerrados: casos con puntaje, distribución del 1 al 5 y promedio.
4. Imprime el resumen en consola. En el desglose de inválidos solo aparecen las reglas que tienen casos. Debajo, la sección `INVALID RECORDS DETAIL` lista cada registro inválido con su ID, su fila en el archivo (el encabezado es la fila 1) y sus motivos, por ejemplo `BRS-000044 (row 45): Missing location_id`.
5. Pregunta `¿Deseas exportar los resultados a CSV? [s / n]`. Acepta `s`, `si`, `sí`, `y` o `yes`; cualquier otra respuesta, o la falta de entrada, no exporta.

Los porcentajes y el promedio se redondean hacia arriba en caso de empate, por ejemplo 2.25 → 2.3.

## Exportación

El resultado se guarda en `data/process/results.csv`, lances el comando desde donde lo lances, y sobrescribe la exportación anterior. El archivo está ignorado en Git.

Hay una fila por métrica, con las columnas `metric`, `value` y `percentage`. Esta última queda vacía cuando no aplica.

| Métrica | Valor | Porcentaje |
|---|---|---|
| `total_records` | Filas del archivo | — |
| `valid_records`, `invalid_records` | Registros | Sobre el total |
| `invalid.<regla>` | Registros que incumplen la regla. Las 7 reglas aparecen siempre, aunque estén en 0 | — |
| `category.<CODE>`, `status.<CODE>` | Registros válidos | Sobre los válidos |
| `satisfaction.closed_cases`, `satisfaction.scored_cases` | Casos cerrados válidos y casos con puntaje | — |
| `satisfaction.average` | Promedio con 2 decimales | — |
| `satisfaction.score_1` … `score_5` | Casos con ese puntaje | Sobre los casos con puntaje |

## Pruebas

```bash
python -m unittest -v
```

Las 32 pruebas comprueban:

- que el CSV provisto da exactamente los valores esperados del briefing: 100 registros, 96 válidos, 4 inválidos y promedio 3.46;
- el detalle de cada registro inválido: ID, fila y motivos;
- cada regla, con sus casos límite;
- la carga del archivo;
- la exportación y la pregunta final.

## Ubicación

El briefing proponía la carpeta `incidents-analysis/` en la raíz. El script está en `scripts/incident-report/` porque la consigna lo pide en `/scripts` y porque el monorepo no admite implementación suelta en la raíz.
