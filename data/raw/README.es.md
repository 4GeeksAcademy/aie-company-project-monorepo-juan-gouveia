# Carpeta `data/raw`

Esta carpeta está pensada para almacenar **datos en bruto** (raw) relacionados con la compañía: dumps, exports, archivos de ejemplo, muestras de eventos, o datasets sin transformar.

- **Propósito principal**: servir como zona de aterrizaje o referencia de datos originales antes de ser procesados por pipelines.
- **Recomendación**: documenta el origen de cada dataset, formato, tamaño esperado, consideraciones de privacidad/PII y cómo se versiona (idealmente evitando subir datos sensibles al repositorio).

## Datasets

### `incidents-brasaland.csv`

- **Origen:** archivo de prueba del briefing de Operaciones. Es la exportación de la hoja de cálculo compartida donde los gerentes de sede registraban los incidentes operativos.
- **Contenido:** 100 incidentes de enero de 2024 en las 14 sedes (`COL-01`…`COL-10` y `FLA-01`…`FLA-04`). Son datos de prueba, con 4 registros inválidos a propósito.
- **Formato:** UTF-8, separado por comas y con encabezado. Columnas: `incident_id`, `date`, `location_id`, `category`, `description`, `status`, `customer_id`, `satisfaction_score` y `reporter_id`.
- **Privacidad:** los IDs de cliente (`CLI-XXXXXX`) y de gerente (`MGR-XX`) son códigos, sin nombres ni datos de contacto.
- **Versionado:** se conserva tal como se recibió; no se modifica. Lo procesa [`scripts/incident-report/`](../../scripts/incident-report/README.es.md).
