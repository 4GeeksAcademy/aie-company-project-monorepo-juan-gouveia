# Carpeta `services`

Esta carpeta contiene **todos los servicios backend** (APIs y workers en segundo plano) relacionados con la compañía para el proyecto transversal de AI Engineering.

Cada subcarpeta dentro de `services/` debe corresponder a **un servicio concreto** (por ejemplo `admin-api`, `data-processor-worker`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar toda la lógica backend, APIs y consumidores de colas que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) los servicios que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlos.

## Servicios

| Servicio | Qué hace |
|---|---|
| [`brasaland-api/`](./brasaland-api/README.es.md) | API central de Brasaland (FastAPI), organizada por dominios. Implementa los dominios `incidents` (análisis del CSV de incidentes y exportación de resultados) , `suppliers` (directorio de proveedores en TinyDB) e `inventory` (inventario de ingredientes en Supabase con SQLModel), además de la autenticación con JWT (`auth`, `users` y `profiles`, en TinyDB). |
| [`telemetry/`](./telemetry/README.es.md) | Pipeline de análisis del reporte técnico de telemetría (`analysis.py`, con Pandas): métricas operacionales por día sobre `telemetry_events`. Es un paquete Python (`brasaland-telemetry`) que la API instala en modo editable; no es un servicio que se ejecute por sí solo. |
| [`jobs/`](./jobs/README.es.md) | Control de estado de los jobs programados (`job_runner`, paquete `brasaland-jobs`): la máquina de estados de `ops.job_runs`, con `processing` como lock e idempotencia por fecha. Lo usa el script nocturno de telemetría (`scripts/nightly_export.py`); no depende de la API. Su `Dockerfile` es la imagen del servicio `nightly-scheduler` (supercronic). |
| [`tasks/`](./tasks/README.es.md) | Cola de tareas asíncronas (paquete `brasaland-tasks`, ticket #DEV-55): la aplicación Celery con Redis como broker y backend de resultados, y las colas `default` y `dead_letter`. El worker es un proceso propio, fuera de FastAPI. |

## Docker

La API corre en el contenedor `api`: [`Dockerfile`](./Dockerfile) (Python 3.12 slim, `uv pip install -r requirements.txt` y Uvicorn con `--reload`). [`requirements.txt`](./requirements.txt) se genera desde `brasaland-api/uv.lock`; su cabecera explica cómo regenerarlo. Se levanta desde la raíz del repositorio con `docker compose up`; ver [Ejecutar con Docker](../README.es.md#ejecutar-con-docker).
