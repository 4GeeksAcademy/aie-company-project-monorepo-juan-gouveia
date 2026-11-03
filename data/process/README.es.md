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
