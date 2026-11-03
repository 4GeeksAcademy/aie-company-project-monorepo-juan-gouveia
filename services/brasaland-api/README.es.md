# Brasaland API (`services/brasaland-api`)

API central de Brasaland, hecha con FastAPI y organizada por dominios según [`docs/ARCHITECTURE_PROPOSAL.md`](../../docs/ARCHITECTURE_PROPOSAL.md). Por ahora implementa el primer dominio, `incidents`: el análisis del CSV de incidentes operativos que usan Operaciones y el backoffice.

> _Versión en inglés: [README.md](./README.md)._

## Estado

- **Implementado:** dominio `incidents` y `GET /health`.
- **Aún no existe:** base de datos, autenticación ni configuración por entorno. Las rutas no están protegidas, así que el servicio **no debe publicarse** todavía.
- **El último análisis se guarda en memoria** y se pierde al reiniciar la API. Cuando haya base de datos, solo cambia `repository.py`.

## Requisitos

Python 3.11 o superior (probado con 3.12).

## Instalación y ejecución

Desde esta carpeta, en Windows:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

En macOS o Linux, sustituye `.venv\Scripts\python` por `.venv/bin/python`.

- Documentación interactiva: http://localhost:8000/docs
- Contrato de la API: http://localhost:8000/openapi.json

## Pruebas

```bash
.venv\Scripts\python -m pytest -v
```

Las 24 pruebas cubren:

- la lectura del archivo y los valores del briefing;
- el JSON del análisis y el CSV exportado;
- cada error de entrada.

Las reglas de validación también las prueban las 32 pruebas del script de consola (`scripts/incident-report/`), que usa el mismo servicio.

## Estructura

```
app/
├── main.py                 # Crea la app, GET /health y registra los routers bajo /api/v1
├── core/errors.py          # Formato único de errores
└── domains/incidents/
    ├── router.py           # Endpoints: solo traducen HTTP
    ├── service.py          # Reglas de validación y análisis (solo librería estándar)
    ├── exceptions.py       # Errores del archivo de incidentes
    ├── schemas.py          # Formato de la respuesta
    ├── repository.py       # Último análisis, en memoria
    └── dependencies.py     # Inyección del repositorio
tests/                      # Replica la estructura de app/
```

`service.py` es la **fuente de verdad** de las reglas de incidentes. Solo usa la librería estándar porque el script `scripts/incident-report/analyze.py` lo importa sin instalar nada.

## Endpoints

### `POST /api/v1/incidents/analyze`

Recibe el CSV como `multipart/form-data` en el campo `file`. Lo valida, lo resume y lo guarda como el último análisis.

La respuesta (200) incluye:

- `source_file` y `analyzed_at`;
- `total_records`, `valid_records` e `invalid_records`;
- `invalid_breakdown`: las 7 reglas, siempre, con su conteo;
- `invalid_records_detail`: ID, fila del archivo (el encabezado es la fila 1) y reglas de cada registro inválido;
- `categories` y `statuses`: código, cantidad y porcentaje sobre los válidos;
- `satisfaction`: casos cerrados, casos con puntaje, promedio y distribución del 1 al 5.

### `GET /api/v1/incidents/results/export`

Descarga el último análisis como `results.csv`, con `Content-Disposition: attachment`. Tiene una fila por métrica, con las columnas `metric`, `value` y `percentage`, igual que la exportación del script.

### `GET /health`

Devuelve `{"status": "ok"}`. Está fuera de `/api/v1` y no lleva autenticación.

## Errores

Todos los errores responden con el formato `{"error": {"code": "...", "message": "..."}}`. El `code` es estable para que lo lea un programa, y el `message` está en español para mostrarlo al usuario.

| Caso | HTTP | `code` |
|---|---|---|
| No se envió el campo `file` | 400 | `missing_file` |
| El archivo no tiene extensión `.csv` | 415 | `unsupported_file_type` |
| El archivo está vacío | 400 | `empty_file` |
| Supera 5 MB | 413 | `file_too_large` |
| No está en UTF-8 | 422 | `invalid_encoding` |
| Faltan columnas; el mensaje dice cuáles | 422 | `missing_columns` |
| Solo tiene el encabezado | 422 | `no_records` |
| Export sin análisis previo | 404 | `no_analysis` |
| Petición mal formada | 422 | `invalid_request` |

El tipo de archivo se valida por la extensión, no por el `Content-Type`, porque Windows envía los CSV como `application/vnd.ms-excel`.

## Quién la usa

- **`uis/backoffice`:** a través de su intermediario `app/api/[...path]/route.ts` (patrón BFF), con la variable de servidor `API_BASE_URL=http://localhost:8000/api/v1`. El navegador nunca llama a la API directamente, así que no hace falta CORS.
- **`scripts/incident-report/analyze.py`:** importa `service.py` directamente; no usa HTTP.

## Diferencias con la consigna del curso

La consigna pide `/services/api` y las rutas `/api/incidents/...`. Este servicio sigue la propuesta de arquitectura (`services/brasaland-api/` y `/api/v1/...`) por dos motivos:

- es el contrato acordado para todo el backend: una carpeta por servicio y una sola versión de la API (secciones 2.2 y 3.1);
- desviarse en el primer dominio implementado rompería esa coherencia.

Desde el navegador, las rutas se ven igual que en la consigna: el backoffice expone `/api/incidents/...` y su intermediario las reenvía a `/api/v1/incidents/...`.
