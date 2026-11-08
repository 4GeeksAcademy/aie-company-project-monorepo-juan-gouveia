# Brasaland API (`services/brasaland-api`)

API central de Brasaland, hecha con FastAPI y organizada por dominios según [`docs/ARCHITECTURE_PROPOSAL.md`](../../docs/ARCHITECTURE_PROPOSAL.md). Implementa dos dominios:

- **`incidents`:** el análisis del CSV de incidentes operativos que usan Operaciones y el backoffice.
- **`suppliers`:** el directorio de proveedores de Compras, guardado en TinyDB.

> _Versión en inglés: [README.md](./README.md)._

## Estado

- **Implementado:** los dominios `incidents` y `suppliers`, y `GET /health`.
- **Aún no existe:** autenticación ni configuración por entorno, aparte de `BRASALAND_DB_PATH`. Las rutas no están protegidas, así que el servicio **no debe publicarse** todavía.
- **Almacenamiento:**
  - El último análisis de incidentes se guarda en memoria y se pierde al reiniciar la API.
  - Los proveedores se guardan en un archivo TinyDB, `storage/brasaland-db.json`, que se conserva entre reinicios. TinyDB es provisional hasta que exista Postgres con ORM. En los dos dominios, solo `repository.py` y `database.py` conocen el almacenamiento.

## Requisitos

- Python 3.11 o superior (probado con 3.12).
- [uv](https://docs.astral.sh/uv/) para instalar y ejecutar. En Windows: `winget install --id astral-sh.uv -e`. Después de instalarlo, abre una terminal nueva para que el PATH lo incluya.

## Instalación y ejecución

Desde esta carpeta:

```bash
uv sync --extra dev                                 # crea .venv e instala lo fijado en uv.lock
uv run seed                                         # carga los proveedores del briefing (opcional)
uv run uvicorn app.main:app --reload --port 8000
```

- Documentación interactiva: http://localhost:8000/docs
- Contrato de la API: http://localhost:8000/openapi.json

<details>
<summary>Sin uv, con pip</summary>

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"     # en macOS o Linux: .venv/bin/python
.venv\Scripts\seed
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Con pip no se usan las versiones fijadas en `uv.lock`.
</details>

## Pruebas

```bash
uv run pytest -v
```

Las 132 pruebas cubren:

- **`incidents` (24):** la lectura del archivo, los valores del briefing, el JSON del análisis, el CSV exportado y cada error de entrada. Las reglas también las prueban las 32 pruebas del script de consola (`scripts/incident-report/`), que usa el mismo servicio.
- **`suppliers` (108):**
  - el modelo, con los campos y valores exactos del briefing, y cada rechazo con 422;
  - el seeder: que no duplica y que confirma el recuento en consola;
  - el repositorio, incluidas la persistencia y la escritura desde dos procesos;
  - cada endpoint con sus códigos HTTP.

Cada prueba usa una base TinyDB temporal, así que no toca `storage/`.

## Estructura

```
app/
├── main.py                 # Crea la app, GET /health, registra los routers bajo /api/v1 y siembra al arrancar
├── core/errors.py          # Formato único de errores
└── domains/
    ├── incidents/
    │   ├── router.py       # Endpoints: solo traducen HTTP
    │   ├── service.py      # Reglas de validación y análisis (solo librería estándar)
    │   ├── exceptions.py   # Errores del archivo de incidentes
    │   ├── schemas.py      # Formato de la respuesta
    │   ├── repository.py   # Último análisis, en memoria
    │   └── dependencies.py # Inyección del repositorio
    └── suppliers/
        ├── models.py       # Modelos Pydantic: Supplier, SupplierCreate, RateUpdate, StatusUpdate
        ├── database.py     # Inicialización de TinyDB y ruta del archivo
        ├── repository.py   # Consultas y escrituras; lo único que conoce TinyDB
        ├── router.py       # Endpoints de /suppliers
        ├── seed.py         # Proveedores iniciales del briefing (`uv run seed`)
        ├── exceptions.py   # DuplicateSupplierError
        └── dependencies.py # Inyección del repositorio
storage/                    # brasaland-db.json (TinyDB); ignorado en Git
tests/                      # Replica la estructura de app/
```

`incidents/service.py` es la **fuente de verdad** de las reglas de incidentes. Solo usa la librería estándar porque el script `scripts/incident-report/analyze.py` lo importa sin instalar nada.

## Dominio `incidents`

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

## Dominio `suppliers`

Es la fuente de verdad única del directorio de proveedores de Brasaland, que sustituye a la hoja de cálculo de Compras.

### Modelo

Los nombres y valores son exactamente los del briefing:

| Campo | Tipo | Reglas |
|---|---|---|
| `name` | texto, requerido | No vacío; único sin distinguir mayúsculas ni espacios extremos |
| `country` | texto, requerido | `"Colombia"` o `"USA"` |
| `categories` | lista, requerida | Al menos 1, sin repetir, de `carne`, `verduras_y_hortalizas`, `salsas_y_condimentos`, `bebidas`, `packaging`, `productos_limpieza`, `lacteos`, `carbon_y_combustible` |
| `rate_per_unit` | número, requerido | Mayor que 0. No acepta textos, booleanos, NaN ni infinito |
| `currency` | texto, requerido | `"COP"` para Colombia y `"USD"` para USA |
| `status` | texto, requerido | `"active"` o `"suspended"` |
| `contact_email` | texto, opcional | Email válido |
| `notes` | texto, opcional | Hasta 1000 caracteres |
| `id` | entero, generado | `doc_id` que asigna TinyDB |
| `updated_at` | fecha, generada | UTC; se fija al crear y cada vez que cambia `rate_per_unit` |

El cliente no puede enviar `id` ni `updated_at`, ni ningún campo desconocido: la API responde 422.

### Endpoints

| Endpoint | Éxito | Errores |
|---|---|---|
| `POST /api/v1/suppliers` | 201 con el proveedor completo y su `id` | 422 si la entrada no es válida; 409 `duplicate_supplier` si el nombre ya existe |
| `GET /api/v1/suppliers?country=&category=` | 200. Sin parámetros, todos; los filtros se pueden combinar | 422 si un filtro tiene un valor desconocido |
| `GET /api/v1/suppliers/{id}` | 200 | 404 `supplier_not_found` |
| `PATCH /api/v1/suppliers/{id}/rate` | 200 con `{"rate_per_unit": ...}`. Actualiza `updated_at` | 404; 422 si la tarifa es ≤ 0 o falta |
| `PATCH /api/v1/suppliers/{id}/status` | 200 con `{"status": ...}`. No cambia `updated_at`, que es la fecha de la última tarifa | 404; 422 si el estado no es válido |
| `DELETE /api/v1/suppliers/{id}` | 200 con el proveedor eliminado | 404 |

Según el briefing, los proveedores no se borran: se suspenden. `DELETE` solo existe para corregir datos erróneos.

### Seeder y archivo TinyDB

- **`uv run seed`:** inserta los 15 proveedores del briefing que no existan, comparando por nombre. Termina con un mensaje como `Seeder completado: 15 proveedores insertados, 0 ya existían. Total en la base: 15 (...)`. Ejecutarlo de nuevo no duplica nada.
- **Al arrancar la API:** siembra solo si la tabla está vacía, así la demo nunca empieza vacía. Un proveedor eliminado con `DELETE` no reaparece al reiniciar; `uv run seed` sí lo restaura.
- **Archivo:** `storage/brasaland-db.json`, en UTF-8 y legible, ignorado en Git. Se puede cambiar con la variable `BRASALAND_DB_PATH`.
- **Volver a los datos iniciales:** borra el archivo y reinicia la API, o ejecuta `uv run seed`.
- **Dos procesos sobre el mismo archivo:** el repositorio no usa caché y calcula cada ID a partir del archivo, así que `uv run seed` puede ejecutarse con la API arrancada. Aun así, TinyDB no está pensado para muchos procesos escribiendo a la vez. Es suficiente para un directorio de unos 20 proveedores que gestiona un equipo pequeño.

## `GET /health`

Devuelve `{"status": "ok"}`. Está fuera de `/api/v1` y no lleva autenticación.

## Errores

Todos los errores responden con el formato `{"error": {"code": "...", "message": "..."}}`. El `code` es estable para que lo lea un programa, y el `message` está en español para mostrarlo al usuario. Los errores de validación añaden `details`, una lista de `{"field", "message"}` que indica qué campo falló y por qué.

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
| Proveedor inexistente | 404 | `supplier_not_found` |
| Ya existe un proveedor con ese nombre | 409 | `duplicate_supplier` |
| Petición mal formada o datos que no cumplen el modelo | 422 | `invalid_request` (con `details`) |

El tipo de archivo de incidentes se valida por la extensión, no por el `Content-Type`, porque Windows envía los CSV como `application/vnd.ms-excel`.

Ejemplo de 422:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "La petición no es válida. Revisa: currency, status.",
    "details": [
      {"field": "currency", "message": "Un proveedor de USA debe usar USD."},
      {"field": "status", "message": "Debe ser uno de estos valores: 'active' o 'suspended'."}
    ]
  }
}
```

## Quién la usa

- **`uis/backoffice`:** a través de su intermediario `app/api/[...path]/route.ts` (patrón BFF), con la variable de servidor `API_BASE_URL=http://localhost:8000/api/v1`. El navegador nunca llama a la API directamente, así que no hace falta CORS. Lo usan las herramientas `/incidencias` y `/proveedores`.
- **`scripts/incident-report/analyze.py`:** importa `incidents/service.py` directamente; no usa HTTP.

## Diferencias con la consigna del curso

Las consignas piden `/services/api`, con rutas como `/api/incidents/...` o `/suppliers`, y archivos sueltos (`main.py`, `models.py`, `database.py`, `routes/suppliers.py`, `seed.py`). Este servicio sigue la propuesta de arquitectura: `services/brasaland-api/`, un dominio por carpeta y `/api/v1/...`. Lo hace por dos motivos:

- es el contrato acordado para todo el backend: una carpeta por servicio y una sola versión de la API (secciones 2.2 y 3.1);
- un segundo servicio por cada ejercicio duplicaría entornos, puertos y reglas.

Los nombres de archivo de la consigna se conservan dentro del dominio `suppliers`. Desde el navegador, las rutas se ven como en la consigna: el backoffice expone `/api/suppliers` e `/api/incidents/...`, y su intermediario las reenvía a `/api/v1/...`.

Todas las divergencias con los briefings y las consignas, con sus motivos, están en [`docs/BRIEFING_DIVERGENCES.md`](../../docs/BRIEFING_DIVERGENCES.md).
