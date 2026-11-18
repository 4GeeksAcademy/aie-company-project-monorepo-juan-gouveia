# Brasaland API (`services/brasaland-api`)

API central de Brasaland, hecha con FastAPI y organizada por dominios según [`docs/ARCHITECTURE_PROPOSAL.md`](../../docs/ARCHITECTURE_PROPOSAL.md). Implementa estos dominios:

- **`incidents`:** el análisis del CSV de incidentes operativos que usan Operaciones y el backoffice, y el gestor de incidencias centralizado (registro, seguimiento y métricas).
- **`suppliers`:** el directorio de proveedores de Compras, guardado en TinyDB.
- **`auth`, `users` y `profiles`:** inicio de sesión con JWT, usuarios (solo credenciales) y perfiles (nombre y contacto), guardados en TinyDB (ticket AUTH-01).
- **`inventory`:** ingredientes, entradas de proveedores y salidas por consumo o merma, con el stock calculado a partir de las órdenes. Se guarda en Supabase (PostgreSQL) con SQLModel (Hito 5, ticket BRD-0512).

> _Versión en inglés: [README.md](./README.md)._

## Estado

- **Implementado:** los dominios `incidents`, `suppliers` e `inventory`, la autenticación (`/auth`, `/users`, `/profiles`) y `GET /health`.
- **Inventario (Hito 5, rama `feature/inventory-orm`):** 6 rutas bajo `/api/v1/inventory`, con el stock calculado y sin ninguna forma de editarlo directamente. Ver [Dominio `inventory`](#dominio-inventory).
- **Contraseñas (AUTH-03, rama `feature/password-reset`):** restablecimiento por correo (Resend) y cambio con la sesión iniciada. Ver [Restablecimiento y cambio de contraseña](#restablecimiento-y-cambio-de-contraseña).
- **Gestor de incidencias (rama `feature/incident-manager`):** alta, listado con filtros, detalle, cambio de estado y métricas. Ver [Gestor de incidencias centralizado](#gestor-de-incidencias-centralizado).
- **Rutas protegidas (AUTH-01):** todas las rutas exigen un token válido salvo `POST /auth/login`, `POST /users` (registro), `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/reset-password/validate` (las tres de AUTH-03) y `GET /health`. Eso incluye las 7 de `incidents` (2 del analizador y 5 del gestor) las 6 de `suppliers` y las 6 de `inventory`, que se protegen al registrar sus routers en `main.py`. Una prueba recorre el esquema OpenAPI y falla si una ruta nueva queda sin proteger por olvido.
- **Almacenamiento:**
  - El último análisis de incidentes se guarda en memoria y se pierde al reiniciar la API.
  - Los proveedores y las incidencias del gestor se guardan en un archivo TinyDB, `storage/brasaland-db.json`, que se conserva entre reinicios. Cada uno tiene su tabla, y comparten un bloqueo por archivo. TinyDB es provisional hasta que exista Postgres con ORM.
  - Los usuarios, los perfiles y los enlaces de restablecimiento de contraseña (`password_resets`) se guardan en otro archivo TinyDB, `storage/auth-db.json`. Por directiva del briefing, usuarios y perfiles se quedarán en TinyDB también cuando llegue PostgreSQL.
  - Las inserciones en ese archivo calculan el ID del documento leyendo el archivo, así que no chocan con escrituras de otro proceso (por ejemplo, `uv run create-admin` con la API arrancada).
  - En los dominios de TinyDB, solo `repository.py` y `database.py` conocen el almacenamiento.
  - El inventario se guarda en **Supabase** (PostgreSQL) con SQLModel: tablas `ingredients`, `ingredient_entries` e `ingredient_exits`. La conexión está en `app/core/database.py` y la API mantiene a la vez las dos conexiones: TinyDB para la autenticación y Supabase para el inventario. Ninguna tabla de usuarios se replica en Supabase: las órdenes solo guardan el `user_uuid` de TinyDB.

## Requisitos

- Python 3.11 o superior (probado con 3.12).
- [uv](https://docs.astral.sh/uv/) para instalar y ejecutar. En Windows: `winget install --id astral-sh.uv -e`. Después de instalarlo, abre una terminal nueva para que el PATH lo incluya.

## Instalación y ejecución

Desde esta carpeta:

```bash
uv sync --extra dev                                 # crea .venv e instala lo fijado en uv.lock
cp .env.example .env                                # y rellena SECRET_KEY y DATABASE_URL (ver abajo)
uv run seed                                         # carga los proveedores del briefing (opcional)
uv run create-admin                                 # crea el primer administrador (necesario para la semilla del inventario)
uv run --env-file .env seed-inventory               # carga en Supabase el inventario del briefing
uv run --env-file .env uvicorn app.main:app --reload --port 8000
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

Con pip no se usan las versiones fijadas en `uv.lock`, y `uvicorn` necesita `--env-file .env` para cargar la configuración.
</details>

### Variables de entorno

La API **no arranca** si falta `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` o `DATABASE_URL`, o si no son válidas: el error dice qué variable revisar. No tienen valor por defecto en el código. En local se leen del archivo `.env` (ignorado en Git) con `uv run --env-file .env`. La plantilla es [`.env.example`](./.env.example).

| Variable | Obligatoria | Uso |
|---|---|---|
| `SECRET_KEY` | Sí | Clave de firma de los JWT, de al menos 32 caracteres. Genera una con `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Sí | Minutos de validez del token de acceso (entero mayor que 0) |
| `DATABASE_URL` | Sí | Cadena de conexión PostgreSQL de Supabase para el inventario: **Connect → Session pooler** (funciona por IPv4), con la contraseña de la base de datos en lugar de `[YOUR-PASSWORD]`. **Es un secreto: va solo en `.env`.** Debe empezar por `postgresql://`; la API usa el driver psycopg2. Los caracteres especiales de la contraseña (`@`, `:`, `/`, `#`…) van codificados (`%40`…) |
| `AUTH_DB_PATH` | No | Archivo TinyDB de usuarios y perfiles; por defecto, `storage/auth-db.json` |
| `BRASALAND_DB_PATH` | No | Archivo TinyDB de proveedores; por defecto, `storage/brasaland-db.json` |
| `RESEND_API_KEY` | No | API key de [Resend](https://resend.com/api-keys), con permiso "Sending access". **Es un secreto: va solo en `.env`.** Sin ella, la API arranca, lo avisa en el log y no envía los correos de restablecimiento |
| `EMAIL_FROM` | No | Remitente de los correos; por defecto, `Brasaland <onboarding@resend.dev>`. Sin dominio verificado en Resend, ese remitente solo entrega al email de la cuenta de Resend |
| `FRONTEND_URL` | No | Dirección del backoffice, para el enlace `<FRONTEND_URL>/reset-password?token=...`; por defecto, `http://localhost:3001` |
| `PASSWORD_RESET_EXPIRE_MINUTES` | No | Minutos de validez del enlace de restablecimiento, entre 15 y 60; por defecto, 30. Con un valor fuera de ese rango, la API no arranca |

## Pruebas

```bash
uv sync --extra dev    # pytest, pytest-cov y httpx
uv run pytest          # las 916 pruebas
uv run pytest --cov    # con cobertura de app/
```

El plan de pruebas, las suites, los comandos por suite, la cobertura y los bugs encontrados están en [TESTING.es.md](./TESTING.es.md). Las 916 pruebas se reparten así:

- **Unitarias de autenticación (146, `tests/auth/`, ticket AUTH-088):** la lógica de los 15 endpoints de `auth`, `users` y `profiles` y de los tokens, sin HTTP: camino feliz, caso límite y modo de fallo de cada uno. Con ellas solas, la cobertura de autenticación es del 88 %.
- **Unitarias de proveedores e incidencias (101, `tests/suppliers/` y `tests/incidents/`, ticket API-042):** la lógica de los 6 endpoints de proveedores y los 5 del gestor de incidencias, sin HTTP, con los tres niveles de cada uno. Con ellas solas, la cobertura de los dos dominios es del 84 %.
- **Inventario (80, `tests/inventory/`, Hito 5):** modelos (tablas, FK y SKU único aplicados por la base), schemas con los valores del briefing, los 6 endpoints sin HTTP (stock calculado, 400 sin escritura, `user_uuid` del usuario autenticado), la semilla y el recuento de consultas (sin N+1). Con las de integración y las de la conexión SQL, la cobertura del dominio es del 97 %.
- **Integración HTTP (325, `tests/integration/`, marker `integration`):** el contrato con el backoffice. Cada endpoint de autenticación, de proveedores, de incidencias y de inventario a través de HTTP (login en JSON y en formulario, subida del CSV, códigos de estado, formato de error y cabeceras), y las 13 rutas de `incidents` y `suppliers`, que responden 401 sin token, con un token mal formado, sin firma, caducado o firmado con otra clave. Ninguna ruta queda abierta salvo las públicas declaradas.
- **`core` (81):** la configuración desde el entorno (la API no arranca sin clave ni sin `DATABASE_URL`), la conexión SQL (sesión por petición y driver psycopg2), el hash de contraseñas y los tokens, el envío de correo y las cabeceras de los errores.
- **`incidents` (51, `tests/domains/`):** el servicio del analizador del CSV y el gestor de incidencias (modelo con los valores exactos y repositorio: ciclo de vida, filtros, `/summary` y el seed sin duplicados). Las reglas del CSV también las prueba el script de consola (`scripts/incident-report/`).
- **`suppliers` (67, `tests/domains/`):** el modelo con los valores del briefing, el seeder y el repositorio (incluida la escritura desde dos procesos).
- **`users`, `profiles` y `auth` (65, `tests/domains/`):** modelos, repositorios (incluida la escritura desde otro proceso), el servicio de usuarios y `uv run create-admin`.

Cada prueba usa bases TinyDB temporales, un SQLite temporal en lugar de Supabase (con las claves foráneas activadas) y su propia configuración, así que no toca `storage/` ni Supabase, ni depende del `.env`.

## Estructura

```
app/
├── main.py                 # Crea la app, GET /health, registra los routers bajo /api/v1, valida la configuración, siembra proveedores y crea las tablas de inventario al arrancar
├── core/
│   ├── config.py           # Variables de entorno (JWT, correo y restablecimiento) y API_PREFIX
│   ├── database.py         # Supabase: motor SQLModel (DATABASE_URL, psycopg2), init_db (create_all) y get_db (sesión por petición)
│   ├── security.py         # Hash bcrypt y JWT: tokens de acceso y de restablecimiento (purpose, jti)
│   ├── email.py            # EmailMessage y emisores: Resend, o desactivado sin RESEND_API_KEY
│   ├── storage.py          # brasaland-db.json compartido: ruta, apertura, bloqueo por archivo e insert_with_file_id
│   └── errors.py           # Formato único de errores, 400 de validación del gestor y 500 genérico
└── domains/
    ├── auth/
    │   ├── router.py       # Login, /auth/me y forgot/reset/change-password
    │   ├── dependencies.py # get_current_user, require_admin y la regla "solo tu cuenta o admin"
    │   ├── schemas.py      # LoginRequest, Token, CurrentUser y entradas de contraseña
    │   ├── passwords.py    # Restablecimiento y cambio de contraseña; límite por hora
    │   ├── emails.py       # Correo de restablecimiento (HTML y texto)
    │   ├── models.py       # PasswordReset
    │   └── repository.py   # Tabla password_resets
    ├── users/
    │   ├── models.py       # Role, User, UserCreate, UserUpdate, UserPublic
    │   ├── database.py     # TinyDB de usuarios y perfiles (auth-db.json) con un bloqueo compartido
    │   ├── repository.py   # Consultas y escrituras de usuarios
    │   ├── service.py      # Crear, obtener por ID o email, actualizar, eliminar y autenticar
    │   ├── router.py       # Endpoints de /users
    │   ├── create_admin.py # `uv run create-admin`
    │   ├── exceptions.py   # DuplicateEmailError
    │   └── dependencies.py # Inyección del almacenamiento
    ├── profiles/
    │   ├── models.py       # Profile, ProfileUpdate
    │   ├── repository.py   # Consultas y escrituras de perfiles
    │   └── router.py       # GET y PUT /profiles/me y /profiles/{user_id}
    ├── incidents/
    │   ├── router.py       # Analizador del CSV: endpoints, solo traducen HTTP
    │   ├── service.py      # Reexporta las reglas del CSV de packages/shared (brasaland_shared)
    │   ├── exceptions.py   # Errores del archivo (de packages/shared) y transición no permitida
    │   ├── schemas.py      # Formato de la respuesta del análisis
    │   ├── repository.py   # Último análisis, en memoria
    │   ├── models.py       # Gestor: Incident, enumeraciones del briefing y ciclo de vida
    │   ├── incident_repository.py # Gestor: tablas incidents e incident_seed_log (TinyDB)
    │   ├── manager_router.py # Gestor: endpoints de /incidents
    │   └── dependencies.py # Inyección de los repositorios
    ├── inventory/
    │   ├── models.py       # Modelos ORM (SQLModel): Ingredient, IngredientEntry, IngredientExit
    │   ├── schemas.py      # Schemas Pydantic de petición y respuesta, separados de los modelos
    │   ├── service.py      # Stock calculado en SQL, rechazo de stock negativo y listados sin N+1
    │   ├── router.py       # Endpoints de /inventory
    │   └── seed.py         # Datos semilla del briefing (`uv run seed-inventory`)
    └── suppliers/
        ├── models.py       # Modelos Pydantic: Supplier, SupplierCreate, RateUpdate, StatusUpdate
        ├── database.py     # Tabla de proveedores; la ruta y la apertura vienen de core/storage.py
        ├── repository.py   # Consultas y escrituras; lo único que conoce TinyDB
        ├── router.py       # Endpoints de /suppliers
        ├── seed.py         # Proveedores iniciales del briefing (`uv run seed`)
        ├── exceptions.py   # DuplicateSupplierError
        └── dependencies.py # Inyección del repositorio
storage/                    # brasaland-db.json y auth-db.json (TinyDB); ignorado en Git
tests/                      # Replica la estructura de app/, más auth/ (unitarias de auth), inventory/ e integration/ (HTTP; ver TESTING.es.md)
```

Las reglas del CSV de incidentes están en el paquete compartido [`packages/shared`](../../packages/shared/README.es.md) (`brasaland_shared.incidents`), que también usan `scripts/incident-report/analyze.py` y `scripts/seed_incidents.py`. La API lo instala como dependencia local (`[tool.uv.sources]` en `pyproject.toml`), así que `uv sync` basta; `incidents/service.py` solo reexporta lo que usa el analizador.

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

## Gestor de incidencias centralizado

Registro y seguimiento de incidencias desde el backoffice (rama `feature/incident-manager`). Comparte el prefijo `/incidents` con el analizador del CSV, pero son piezas distintas: el analizador no guarda incidencias.

### Modelo

`Incident` usa exactamente los nombres y valores del briefing:

| Campo | Valores |
|---|---|
| `id` | Entero generado por TinyDB |
| `title` | Obligatorio, de 1 a 120 caracteres |
| `description` | Obligatorio, de 1 a 2.000 caracteres |
| `category` | `equipment_failure`, `supply_issue`, `customer_complaint`, `staff_issue`, `facility_issue`, `pos_system`, `delivery_issue`, `other` |
| `status` | `open`, `in_progress`, `resolved`, `discarded` |
| `origin` | `customer`, `branch`, `internal` |
| `branch` | Obligatorio en todos los orígenes: `central` y las 14 sedes del briefing (`medellin_centro` … `fort_lauderdale`) |
| `created_at`, `updated_at` | Fecha y hora en UTC, generadas por el sistema |

- Toda incidencia nueva empieza en `open`: `POST` acepta `status` solo con ese valor.
- Ciclo de vida: `open → in_progress | discarded`; `in_progress → resolved | discarded`. `resolved` y `discarded` son finales.
- Se guarda en la tabla `incidents` de `storage/brasaland-db.json`, el mismo archivo que los proveedores y con su mismo bloqueo (`core/storage.lock_for`), porque TinyDB reescribe el archivo entero en cada escritura.

### Endpoints

| Método y ruta | Respuesta | Errores |
|---|---|---|
| `POST /api/v1/incidents` | 201 con la incidencia | 400 `invalid_request` (con `details`) |
| `GET /api/v1/incidents` | 200 con la lista, de la más reciente a la más antigua. Filtros opcionales `status`, `origin`, `branch` y `category`, combinables | 400 si un filtro no es válido |
| `GET /api/v1/incidents/summary` | 200 con `total`, `by_status`, `by_category`, `by_origin` y `by_branch`; cada desglose incluye todos los valores, también en 0 | — |
| `GET /api/v1/incidents/{id}` | 200 con la incidencia | 404 `incident_not_found` |
| `PATCH /api/v1/incidents/{id}/status` | 200 con la incidencia; cambia solo `status` y `updated_at` | 400 `invalid_transition` (el mensaje dice a qué estados se puede pasar) o `invalid_request`; 404 |

- **Errores de validación con 400:** en estas rutas, como pide su consigna, un campo que falta o un valor no permitido responde 400, con el mismo cuerpo que el 422 del resto de la API. Las demás rutas siguen respondiendo 422.
- **Base vacía:** la lista es `[]` y las métricas, 0.

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

## Dominio `inventory`

Inventario centralizado de ingredientes (Hito 5, ticket BRD-0512). La regla de Operaciones es que **el stock no se modifica directamente**: solo cambia registrando una orden de entrada (entrega de proveedor) o de salida (consumo o merma), y cada orden es trazable al usuario que la creó. Los datos viven en Supabase (PostgreSQL) y se modelan con SQLModel.

### Modelo

Los nombres de entidades y campos son exactamente los del briefing. Los modelos ORM (`models.py`) y los schemas de la API (`schemas.py`) son clases distintas: ningún endpoint devuelve un objeto ORM.

| Entidad (tabla) | Campos | Reglas |
|---|---|---|
| `Ingredient` (`ingredients`) | `id`, `name`, `sku`, `unit`, `category`, `country` | `sku` único; `unit`: `kg`, `litro` o `unidad`; `category`: `meat`, `produce`, `sauce`, `beverage`, `packaging` o `cleaning`; `country`: `CO` o `US`. **Sin columna de stock**: `current_stock` solo existe en la respuesta |
| `IngredientEntry` (`ingredient_entries`) | `id`, `ingredient_id` (FK), `quantity`, `supplier_name`, `location_id`, `created_at`, `user_uuid` | `quantity` > 0; `location_id` de 1 a 14 (no es FK) |
| `IngredientExit` (`ingredient_exits`) | `id`, `ingredient_id` (FK), `quantity`, `reason`, `location_id`, `created_at`, `user_uuid` | `reason`: `consumption` o `waste` |

- **`current_stock`** = suma de las entradas − suma de las salidas del ingrediente, calculado por la base de datos en cada lectura. El alcance es global por ingrediente: `location_id` se guarda, pero no parte el stock.
- **`user_uuid`** es el `id` de TinyDB del usuario autenticado; lo pone la API a partir del token. Enviarlo en el cuerpo da 422. No es FK: los usuarios no se replican en Supabase.
- **`created_at`** lo pone la API, en UTC.

### Endpoints

Todos exigen token. El router tiene el prefijo `/inventory` y se monta bajo `/api/v1`.

| Método y ruta | Uso | Respuestas |
|---|---|---|
| `GET /api/v1/inventory/products` | Ingredientes con `current_stock`; `?country=CO` o `US` filtra por mercado | 200, 422 |
| `POST /api/v1/inventory/products` | Crea un ingrediente; nace con stock 0 | 201, 409 `duplicate_sku`, 422 |
| `GET /api/v1/inventory/products/{id}` | Un ingrediente con su stock actual | 200, 404 `ingredient_not_found` |
| `POST /api/v1/inventory/orders/inbound` | Registra una entrega de proveedor (`IngredientEntry`) | 201, 404, 422 |
| `POST /api/v1/inventory/orders/outbound` | Registra un consumo o una merma (`IngredientExit`) | 201, **400 `insufficient_stock`**, 404, 422 |
| `GET /api/v1/inventory/orders` | `{"inbound": [...], "outbound": [...]}` con los datos del ingrediente y el `user_uuid`, de la más reciente a la más antigua | 200 |

Una salida que dejaría el stock en negativo se rechaza **antes de escribir nada**:

```json
{"error": {"code": "insufficient_stock", "message": "Stock insuficiente para el ingrediente 'Falda de ternera'. Disponible: 52, solicitado: 60."}}
```

La salida bloquea la fila del ingrediente (`SELECT ... FOR UPDATE`) mientras calcula el stock, así que dos salidas simultáneas no pueden gastar el mismo stock. No hay rutas para editar ni borrar ingredientes u órdenes.

### Consultas sin N+1

La API solo usa `sqlmodel` (`select`, `func`, `col`), sin SQLAlchemy directo. `GET /products` es una sola consulta (ingredientes con dos subconsultas que suman entradas y salidas) y `GET /orders` son dos (una por tabla, con un `join` al ingrediente), haya las filas que haya. `tests/inventory/test_queries.py` lo comprueba contando las sentencias SQL.

### Semilla

`uv run --env-file .env seed-inventory` carga en Supabase los datos semilla del briefing:

- los 6 ingredientes de la tabla;
- 4 entradas: Falda de ternera 50 y 30 kg (Carnes del Valle S.A.), Costilla de cerdo 40 kg (MiamiMeat Co.) y Chimichurri 20 litros (Salsas Artesanales Ltda.);
- 3 salidas: Falda de ternera 25 kg de consumo y 3 kg de merma, y Costilla de cerdo 8 kg de consumo.

Stock resultante: Falda de ternera 52, Costilla de cerdo 32, Chimichurri 20 y el resto 0.

- Las órdenes llevan el UUID del administrador activo más antiguo de TinyDB: antes hay que ejecutar `uv run create-admin`.
- Crea las tablas si no existen, valida los datos con los schemas de la API y lo inserta todo en una única transacción.
- Es idempotente: si ya hay ingredientes, no inserta nada.
- `location_id` es 1 para los ingredientes de Colombia y 10 para los de EE. UU. (valores de ejemplo: el briefing no asigna locales a países).
- La API no siembra el inventario al arrancar.

## Autenticación: `auth`, `users` y `profiles`

Ninguna ruta que exponga o modifique datos sensibles debe responder sin una sesión válida (ticket AUTH-01). La API es **stateless**: no hay sesiones de servidor ni cookies. El login devuelve un JWT y cada petición protegida lo envía en la cabecera `Authorization: Bearer <token>`.

### Modelos

- **`User`** guarda solo credenciales: `id` (UUID4), `email` (único, en minúsculas), `hashed_password` (bcrypt), `is_active`, `role` y `created_at`. El hash nunca sale en una respuesta.
- **`role`** solo admite `admin`, `manager` o `user`. El registro siempre crea `user`.
- **`Profile`** guarda el nombre visible y el contacto: `id`, `user_id`, `name`, `phone` y `address`. Se crea con el usuario y se borra con él.
- **Contraseña:** de 8 caracteres a 72 bytes (límite de bcrypt). Se hashea con libpass (`from passlib.hash import bcrypt`); el texto plano nunca se guarda ni se compara.
- **Otros módulos** referencian al usuario por su `id` con el nombre `user_uuid`. Los usuarios y perfiles no se copian a otras bases.

### Token

- Firmado con HS256 (`python-jose`) con `SECRET_KEY`. Caduca a los `ACCESS_TOKEN_EXPIRE_MINUTES` minutos.
- Lleva solo `sub` (el `id` del usuario), `iat` y `exp`. El rol se lee de la base en cada petición, así que un cambio de rol o una desactivación aplica sin esperar a que caduque el token.

### Endpoints

| Endpoint | Acceso | Éxito | Errores |
|---|---|---|---|
| `POST /api/v1/auth/login` | Público | 200 `{access_token, token_type: "bearer"}` | 401 `invalid_credentials`, 403 `inactive_user`, 415, 422 |
| `GET /api/v1/auth/me` | Token | 200 con `id`, `email`, `role` y `profile` | 401, 403 |
| `POST /api/v1/users` | Público (registro) | 201 con el usuario y su perfil | 409 `duplicate_email`, 422 (también si se envía `role`) |
| `GET /api/v1/users` | Solo admin | 200 con la lista | 401, 403 |
| `GET /api/v1/users/{id}` | La propia cuenta o admin | 200 | 401, 403, 404 `user_not_found` |
| `PUT /api/v1/users/{id}` | La propia cuenta o admin. `role` e `is_active`, solo admin | 200 | 401, 403, 404, 409, 422 |
| `DELETE /api/v1/users/{id}` | La propia cuenta o admin | 200 con el usuario eliminado (también borra su perfil) | 401, 403, 404 |
| `GET /api/v1/profiles/me` | Token | 200 | 401, 404 `profile_not_found` |
| `PUT /api/v1/profiles/me` | Token (solo el propio perfil) | 200 | 401, 404, 422 |
| `GET /api/v1/profiles/{user_id}` | El propio perfil o admin | 200 | 401, 403 `forbidden`, 404 (solo admin) |
| `PUT /api/v1/profiles/{user_id}` | Solo el dueño del perfil, también frente a un admin | 200 | 401, 403 `forbidden`, 404, 422 |

- **Login:** acepta JSON `{"email", "password"}` y también el formulario `username`/`password` que envía el botón «Authorize» de `/docs` (`username` es el email). Si el email no existe o la contraseña falla, la respuesta es la misma, y bcrypt se ejecuta en ambos casos para no revelar qué emails están registrados.
- **`PUT`:** cambia solo los campos enviados. En los perfiles, `null` vacía un campo.
- **403 entre usuarios:** un usuario que no es admin recibe 403 al acceder a otra cuenta, exista o no ese ID, para no revelar qué IDs existen.
- **Primer administrador:** `uv run create-admin` pide el email y la contraseña (sin mostrarla) y crea el admin. Si el email ya existe, lo hace admin y lo reactiva sin cambiar su contraseña. Después, un admin cambia roles con `PUT /users/{id}`.

### Restablecimiento y cambio de contraseña

Ticket AUTH-03. El correo se envía con [Resend](https://resend.com), elegido frente a SendGrid porque su plan gratuito no caduca y permite completar el flujo sin dominio propio. Los motivos completos están en `docs/BRIEFING_DIVERGENCES.md`.

| Endpoint | Acceso | Éxito | Errores |
|---|---|---|---|
| `POST /api/v1/auth/forgot-password` | Público | 200 siempre, con el mismo mensaje | 422 si el email no tiene un formato válido |
| `POST /api/v1/auth/reset-password/validate` | Público | 200 si el enlace sirve (no lo consume) | 400 `invalid_reset_token`, `reset_token_expired` o `reset_token_used`; 422 |
| `POST /api/v1/auth/reset-password` | Público | 200 | 400 (mismos códigos); 422 si la contraseña nueva no cumple las reglas |
| `POST /api/v1/auth/change-password` | Token | 200 con un token de acceso nuevo | 400 `invalid_current_password`, 401, 422 |

- **`forgot-password`** acepta `{email}`. Si el email es de una cuenta activa, crea un enlace `<FRONTEND_URL>/reset-password?token=...` y lo envía **después de responder** (`BackgroundTasks`). Así la respuesta, y su tiempo, son iguales exista o no la cuenta. Si el proveedor falla, solo queda en el log, sin destinatario ni enlace. Como máximo se envían **3 enlaces por cuenta y hora**; los demás se ignoran en silencio.
- **Token del enlace:** JWT firmado con `SECRET_KEY`, con `sub`, `jti`, `iat`, `exp` y `purpose: "password_reset"`. Caduca a los `PASSWORD_RESET_EXPIRE_MINUTES` minutos. Su `jti` tiene una fila en `password_resets`: al usarse se marca y ya no vale. Usar un enlace anula también los demás pendientes del usuario. Un token de restablecimiento no sirve como sesión, ni una sesión como token de restablecimiento.
- **Entradas:** `reset-password` acepta `{token, new_password}` y `change-password`, `{current_password, new_password}`. La contraseña nueva sigue las mismas reglas que en el registro.
- **Sesiones:** restablecer o cambiar la contraseña (también por `PUT /users/{id}`) guarda `password_changed_at`, y los tokens de acceso emitidos antes responden 401 `session_revoked`. `change-password` devuelve un token nuevo para seguir en la sesión actual; `PUT /users/{id}` no, así que quien cambie ahí su propia contraseña vuelve a iniciar sesión. Los dos anulan los enlaces de restablecimiento pendientes. `iat` va en segundos, así que un token emitido en el mismo segundo que el cambio sigue valiendo.
- **Correo:** HTML con estilos en línea, una columna de 600 px como máximo y un botón grande (legible en móvil), y una versión en texto plano.
- **Probarlo sin dominio propio:** registra un usuario con el email de tu cuenta de Resend, añade `RESEND_API_KEY` a `.env` y llama a `forgot-password` con ese email.

### Probarlo en `/docs`

1. `POST /api/v1/users` con `{"email": "...", "password": "..."}`.
2. Botón **Authorize**: escribe el email en `username` y la contraseña. También puedes llamar a `POST /api/v1/auth/login` y copiar el `access_token`.
3. Llama a `GET /api/v1/auth/me`: responde con tu email, tu rol y tu perfil. Sin token responde 401.

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
| CSV mal formado (por ejemplo, una comilla sin cerrar); el mensaje indica la línea | 422 | `malformed_csv` |
| Solo tiene el encabezado | 422 | `no_records` |
| Export sin análisis previo | 404 | `no_analysis` |
| Proveedor inexistente | 404 | `supplier_not_found` |
| Incidencia inexistente | 404 | `incident_not_found` |
| Cambio de estado que el ciclo de vida no permite | 400 | `invalid_transition` |
| Ya existe un proveedor con ese nombre | 409 | `duplicate_supplier` |
| Falta el token de acceso | 401 | `not_authenticated` |
| Token mal formado, con otra firma o de un usuario eliminado | 401 | `invalid_token` |
| Token caducado | 401 | `token_expired` |
| Token emitido antes del último cambio de contraseña | 401 | `session_revoked` |
| Enlace de restablecimiento no válido, caducado o ya usado | 400 | `invalid_reset_token`, `reset_token_expired`, `reset_token_used` |
| Contraseña actual incorrecta en `change-password` | 400 | `invalid_current_password` |
| Email o contraseña incorrectos en el login | 401 | `invalid_credentials` |
| Cuenta desactivada | 403 | `inactive_user` |
| Acceso a otra cuenta, o una operación solo de admin | 403 | `forbidden` |
| Usuario inexistente (solo lo ve un admin) | 404 | `user_not_found` |
| La cuenta no tiene perfil | 404 | `profile_not_found` |
| Ya existe un usuario con ese email | 409 | `duplicate_email` |
| El login no llega en JSON ni como formulario | 415 | `unsupported_media_type` |
| Petición mal formada o datos que no cumplen el modelo | 422 (400 en el gestor de incidencias) | `invalid_request` (con `details`) |
| Error inesperado del servidor | 500 | `internal_error`, con un mensaje genérico; el detalle solo va al log |

Los 401 incluyen la cabecera `WWW-Authenticate: Bearer`.

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

### Comandos de consola

`uv run seed`, `uv run create-admin` y `uv run seed-inventory` escriben el resultado en `stdout` y los errores en `stderr`, sin traceback, y terminan con código 0 si todo va bien y 1 si falla (`create-admin` termina con 130 si se cancela con Ctrl+C). Los dos primeros detectan una base de datos que no se puede abrir, que no es un JSON válido (no se modifica) o que no se puede escribir. `seed-inventory` detecta que falta un administrador o `DATABASE_URL` y los fallos de conexión con Supabase; de estos solo muestra el tipo de error, porque el mensaje del driver puede incluir el host o el usuario de la conexión.

Los dos muestran la ruta absoluta de la base de datos que usan, a propósito: solo la ve quien opera el servidor, en su propia consola, y como `BRASALAND_DB_PATH` y `AUTH_DB_PATH` pueden apuntar a cualquier sitio, es la forma de confirmar qué archivo se modificó. La API nunca devuelve esa ruta a un cliente.

## Quién la usa

- **`uis/backoffice`:** a través de su intermediario `app/api/[...path]/route.ts` (patrón BFF), con la variable de servidor `API_BASE_URL=http://localhost:8000/api/v1`. El navegador nunca llama a la API directamente, así que no hace falta CORS. Lo usan las herramientas `/incidencias` y `/proveedores`, y las vistas de sesión (`/login`, `/register`). El navegador guarda el token en `localStorage` y lo envía en `Authorization: Bearer`; el intermediario lo reenvía tal cual (ticket AUTH-02).
- **`scripts/incident-report/analyze.py`:** usa las mismas reglas que la API, desde `packages/shared`; no usa HTTP.
- **`scripts/seed_incidents.py`:** carga el histórico del CSV en el gestor de incidencias usando el repositorio de la API (`IncidentRepository`) sobre el mismo archivo TinyDB; no usa HTTP.

## Diferencias con la consigna del curso

Las consignas piden `/services/api`, con rutas como `/api/incidents/...` o `/suppliers`, y archivos sueltos (`main.py`, `models.py`, `database.py`, `routes/suppliers.py`, `seed.py`). Este servicio sigue la propuesta de arquitectura: `services/brasaland-api/`, un dominio por carpeta y `/api/v1/...`. Lo hace por dos motivos:

- es el contrato acordado para todo el backend: una carpeta por servicio y una sola versión de la API (secciones 2.2 y 3.1);
- un segundo servicio por cada ejercicio duplicaría entornos, puertos y reglas.

La autenticación sigue la misma pauta: el briefing pide `/auth`, `/users` y `/profiles`, y aquí están bajo `/api/v1`. Además, el login acepta formulario además de JSON, y el registro no admite `role`.

El inventario (Hito 5) también: la consigna pide `services/database.py`, `models.py`, `schemas.py` y `routers/inventory.py`, y aquí es el dominio `app/domains/inventory/`, con las rutas en `/api/v1/inventory`. El motor SQLModel tiene su propio módulo (`app/core/database.py`) para no tocar la configuración TinyDB de auth.

Los nombres de archivo de la consigna se conservan dentro del dominio `suppliers`. Desde el navegador, las rutas se ven como en la consigna: el backoffice expone `/api/suppliers` e `/api/incidents/...`, y su intermediario las reenvía a `/api/v1/...`.

Todas las divergencias con los briefings y las consignas, con sus motivos, están en [`docs/BRIEFING_DIVERGENCES.md`](../../docs/BRIEFING_DIVERGENCES.md).
