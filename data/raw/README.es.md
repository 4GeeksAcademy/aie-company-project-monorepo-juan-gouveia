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

### `telemetry_events/` (pipeline de negocio, fuera de Git)

- **Origen:** la task opcional `save_raw_extract` del [pipeline de desempeño semanal](../pipelines/README.es.md) guarda aquí la extracción de cada corrida, `<run_id>.json`. La fuente es `telemetry_events`, en Supabase; esta copia sirve para auditar qué leyó una corrida.
- **Contenido:** las semanas, el entorno y los eventos de negocio leídos (`id`, `timestamp`, `event_type` y las propiedades de negocio de `tags`).
- **Privacidad:** sin `user_id`, `session_id` ni `request_id` (plan de telemetría, §8).
- **Versionado:** ignorada por Git (`.gitignore` raíz). Se puede borrar: el pipeline no la lee.
