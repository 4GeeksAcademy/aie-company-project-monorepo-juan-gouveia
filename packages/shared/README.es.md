# Paquete compartido (`packages/shared`)

Código reutilizable entre los proyectos del monorepo. Tiene dos partes independientes:

| Parte | Lenguaje | Contenido | Lo consume |
|---|---|---|---|
| `brasaland_shared/` (paquete `brasaland-shared`) | Python, solo librería estándar | Reglas del CSV de incidentes del sistema legacy: validación, análisis y errores del archivo | `scripts/incident-report/analyze.py`, `scripts/seed_incidents.py` y `services/brasaland-api` |
| `types/` (paquete `@repo/shared-types`) | TypeScript | Tipos base (`Id`, `BaseEntity`) | Aún sin consumidores |

> _Versión en inglés: [README.md](./README.md)._

## `brasaland_shared.incidents`

Es la **única** implementación de las reglas del CSV de incidentes (`incidents-brasaland.csv`). El analizador, el seed del gestor de incidencias y la API la importan; ninguno tiene una copia.

| Módulo | Qué contiene |
|---|---|
| `validation.py` | Columnas (`FIELDS`), valores permitidos (`LOCATIONS`, `CATEGORIES`, `STATUSES`), reglas de invalidez (`RULES`, `RULE_LABELS`), lectura (`parse_records`, `load_records`, `parse_upload`) y `validate_record` / `split_records` |
| `analysis.py` | Métricas del reporte (`analyze`, `percentage`, `rounded_average`) y exportación (`build_export_rows`, `export_csv_text`) |
| `exceptions.py` | Errores de un archivo que no se puede analizar (`EmptyFileError`, `InvalidEncodingError`, `MissingColumnsError`, `NoRecordsError`) |

### Cómo se consume

- **Scripts:** añaden `packages/shared` a la ruta de Python e importan `brasaland_shared`. Como el paquete no tiene dependencias, no hace falta instalar nada.
- **API:** lo declara como dependencia local en su `pyproject.toml` (`[tool.uv.sources]`, en modo editable), así que `uv sync` lo instala y los cambios se ven sin reinstalar. `app/domains/incidents/service.py` y `exceptions.py` solo reexportan lo que usa el analizador.

### Por qué aquí

La consigna del gestor de incidencias pide que la validación del proyecto anterior esté en `packages/shared/` y la reutilicen el script y la API sin duplicación. Antes vivía en `services/brasaland-api/app/domains/incidents/service.py`; se movió sin cambiar ninguna regla, y las pruebas del analizador (32 del script y 24 de la API) pasan sin modificarse.

### Pruebas

Las reglas se prueban a través de sus consumidores: las pruebas del script (`scripts/incident-report/test_analyze.py`), las del analizador de la API (`tests/domains/incidents/test_service.py` y `test_router.py`) y las del seed (`scripts/test_seed_incidents.py`).
