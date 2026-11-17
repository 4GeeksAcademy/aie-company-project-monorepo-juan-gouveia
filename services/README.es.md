# Carpeta `services`

Esta carpeta contiene **todos los servicios backend** (APIs y workers en segundo plano) relacionados con la compañía para el proyecto transversal de AI Engineering.

Cada subcarpeta dentro de `services/` debe corresponder a **un servicio concreto** (por ejemplo `admin-api`, `data-processor-worker`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar toda la lógica backend, APIs y consumidores de colas que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) los servicios que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlos.

## Servicios

| Servicio | Qué hace |
|---|---|
| [`brasaland-api/`](./brasaland-api/README.es.md) | API central de Brasaland (FastAPI), organizada por dominios. Implementa los dominios `incidents` (análisis del CSV de incidentes y exportación de resultados) , `suppliers` (directorio de proveedores en TinyDB) e `inventory` (inventario de ingredientes en Supabase con SQLModel), además de la autenticación con JWT (`auth`, `users` y `profiles`, en TinyDB). |

## Docker

La API corre en el contenedor `api`: [`Dockerfile`](./Dockerfile) (Python 3.12 slim, `uv pip install -r requirements.txt` y Uvicorn con `--reload`). [`requirements.txt`](./requirements.txt) se genera desde `brasaland-api/uv.lock`; su cabecera explica cómo regenerarlo. Se levanta desde la raíz del repositorio con `docker compose up`; ver [Ejecutar con Docker](../README.es.md#ejecutar-con-docker).
