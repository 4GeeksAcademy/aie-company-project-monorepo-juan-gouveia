# Tech Context

## Stack Tecnológico

### Frontend (UI)

| Tecnología | Versión | Uso |
|---|---|---|
| **Next.js** | 16.3.5 | Framework principal con App Router |
| **React** | 19.2.8 | Librería de UI |
| **TypeScript** | ^5 | Tipado estático |
| **Tailwind CSS** | ^4 | Estilos utilitarios |
| **PostCSS** | (vía @tailwindcss/postcss) | Procesamiento CSS |
| **ESLint** | ^9 | Linter con `eslint-config-next` (core-web-vitals + TypeScript) |

**Proyectos UI actuales:**

- `uis/website` (puerto 3000) — Landing y registro de Brasa Points para clientes.
- `uis/backoffice` (puerto 3001) — Herramientas internas: Talent Pipeline Tracker (`/talento`), pruebas de funciones (`/funciones`), análisis de incidencias (`/incidencias`) y directorio de proveedores (`/proveedores`). Las dos últimas llaman a la API de Brasaland a través del BFF.

### Backend / Servicios

- **`services/brasaland-api/`** — API central en **FastAPI** (Python ≥ 3.11, Pydantic 2), con la estructura por dominios de la propuesta de arquitectura. Dependencias en `pyproject.toml` (`fastapi`, `uvicorn[standard]`, `python-multipart`, `tinydb`, `pydantic[email]`, `python-jose[cryptography]` y `libpass[bcrypt]`; de desarrollo, `pytest` y `httpx`), gestionadas con **uv** (`uv.lock` versionado) y entorno virtual propio en `.venv/`, ignorado en Git. Comandos: `uv sync --extra dev`, `uv run --env-file .env uvicorn app.main:app --port 8000`, `uv run pytest`, `uv run seed` y `uv run create-admin` (scripts de `[project.scripts]`).
- **Configuración (`app/core/config.py`):** `SECRET_KEY` (mínimo 32 caracteres) y `ACCESS_TOKEN_EXPIRE_MINUTES` son obligatorias y sin valor por defecto; la API no arranca sin ellas. En local van en `services/brasaland-api/.env` (ignorado; plantilla `.env.example`). Opcionales: `AUTH_DB_PATH` y `BRASALAND_DB_PATH`. `API_PREFIX = "/api/v1"` vive aquí.
- **Autenticación (ticket AUTH-01, rama `feature/auth-api`, completada y verificada).**
  - **Modelo:** JWT stateless, sin sesiones ni cookies. `app/core/security.py` hashea con bcrypt (libpass, `from passlib.hash import bcrypt`) y firma con HS256 (python-jose) tokens con solo `sub` (UUID del usuario), `iat` y `exp`.
  - **Dominios:** `users` (solo credenciales: `id` UUID4, `email` único en minúsculas, `hashed_password`, `is_active`, `role` ∈ `admin`/`manager`/`user`, `created_at`; capa `service.py`), `profiles` (`id`, `user_id`, `name`, `phone`, `address`, uno a uno) y `auth` (`POST /auth/login` con JSON o formulario, `GET /auth/me`, `get_current_user`, `require_admin`).
  - **Rutas:** `/api/v1/auth`, `/api/v1/users` (registro público; el resto, la propia cuenta o admin; `GET /users`, `role` e `is_active` solo admin) y `/api/v1/profiles` (`/me`, y `/{user_id}`: leer el dueño o un admin, modificar solo el dueño; 403 en otro caso).
  - **Almacenamiento:** TinyDB en `storage/auth-db.json`, una instancia con un `RLock` compartido por los repositorios de usuarios y perfiles. Por directiva del briefing, usuarios y perfiles se quedan en TinyDB aunque llegue PostgreSQL; otros módulos guardan el `id` como `user_uuid`.
  - **Protección:** `main.py` registra `incidents` y `suppliers` con `dependencies=[Depends(get_current_user)]`. Solo son públicas `POST /auth/login`, `POST /users` y `GET /health`; `tests/test_protected_routes.py` lo comprueba sobre el esquema OpenAPI.
- **Contraseñas y correo (ticket AUTH-03, rama `feature/password-reset`):**
  - **Endpoints:** `POST /auth/forgot-password`, `/auth/reset-password/validate`, `/auth/reset-password` y `/auth/change-password`.
  - **Token del enlace:** JWT `purpose: "password_reset"` con `jti`, más la tabla `password_resets` en `auth-db.json` (un solo uso; anula los pendientes). `decode_access_token_claims` rechaza JWT con `purpose`. `User.password_changed_at` revoca los tokens con `iat` anterior (401 `session_revoked`).
  - **Correo:** `app/core/email.py` (`EmailSender`; `ResendEmailSender` con el SDK `resend`; `DisabledEmailSender` sin `RESEND_API_KEY`; `send_safely` en `BackgroundTasks`). Variables opcionales: `RESEND_API_KEY`, `EMAIL_FROM` (por defecto `onboarding@resend.dev`, que sin dominio solo entrega al email de la cuenta de Resend), `FRONTEND_URL` y `PASSWORD_RESET_EXPIRE_MINUTES` (15–60, por defecto 30).
  - **Pruebas:** usan un emisor falso autouse (`conftest.py`).
  - **TinyDB:** `app/core/storage.py` (`insert_with_file_id`) calcula el `doc_id` desde el archivo en `users`, `profiles` y `password_resets`, para no chocar con escrituras de otro proceso.
- **Dominio `suppliers` (directorio de proveedores, milestone 09).**
  - **Rutas:** `POST/GET /api/v1/suppliers` (filtros `country` y `category`), `GET/DELETE /suppliers/{id}`, `PATCH /suppliers/{id}/rate` y `PATCH /suppliers/{id}/status`.
  - **Modelos (`models.py`):** Pydantic con enums que tienen los valores exactos del briefing. La moneda debe corresponder al país, `extra="forbid"`, y la tarifa es estricta y mayor que 0.
  - **Almacenamiento:** TinyDB en `storage/brasaland-db.json` (ignorado), configurable con `BRASALAND_DB_PATH`. `database.py` y `repository.py` son lo único que conoce TinyDB.
  - **Concurrencia:** el repositorio usa un `Lock`, no usa caché de consultas y calcula el `doc_id` desde el archivo.
  - **`updated_at`:** se fija al crear y en `PATCH /rate`.
  - **Seeder:** `seed.py` tiene los 15 proveedores del briefing. `uv run seed` inserta por nombre, y el `lifespan` de `main.py` siembra solo si la tabla está vacía.
  - **Pruebas:** usan una base temporal mediante un fixture autouse en `tests/conftest.py`.
- **Dominio `incidents`.** `POST /api/v1/incidents/analyze` (multipart, campo `file`) y `GET /api/v1/incidents/results/export` (`text/csv`, adjunto `results.csv`), más `GET /health`. Las reglas del CSV están en `packages/shared` (paquete Python `brasaland_shared`, solo librería estándar), que la API instala como dependencia local con uv y que importan `scripts/incident-report/analyze.py` y `scripts/seed_incidents.py`; `service.py` solo las reexporta. **Gestor de incidencias** (rama `feature/incident-manager`): `POST`/`GET /api/v1/incidents`, `GET /summary`, `GET /{id}` y `PATCH /{id}/status`, con validación 400 y tablas `incidents` e `incident_seed_log` en `brasaland-db.json`; el histórico se carga con `scripts/seed_incidents.py`. El último análisis se guarda en memoria (`repository.py`).
- **Errores:** formato único `{"error": {"code", "message"}}` (`app/core/errors.py`), con mensajes en español y cabeceras opcionales (los 401 llevan `WWW-Authenticate: Bearer`). Autenticación: 401 `not_authenticated` / `invalid_token` / `token_expired` / `invalid_credentials`, 403 `inactive_user` / `forbidden`, 404 `user_not_found` / `profile_not_found`, 409 `duplicate_email`, 415 `unsupported_media_type`. Resto: 400 `missing_file` / `empty_file`, 413 `file_too_large` (5 MB), 415 `unsupported_file_type` (por extensión), 422 `invalid_encoding` / `missing_columns` / `no_records` / `invalid_request`, 404 `no_analysis` / `not_found` / `supplier_not_found`, 409 `duplicate_supplier`. Los 422 de validación (`invalid_request`) incluyen `details: [{field, message}]` con mensajes en español (`describe_validation_errors`).
- **Desviación de la consigna, a justificar en la entrega:** se usan `services/brasaland-api/` y `/api/v1` (propuesta) en vez de `/services/api` y `/api/incidents/...`. Esta y las demás divergencias con briefings y consignas se registran en `docs/BRIEFING_DIVERGENCES.md`.
- El tracker consume actualmente una API REST de playground mediante `NEXT_PUBLIC_API_BASE_URL` con endpoints:
  - `GET /records` — listar candidatos (filtrable por status, stage, search)
  - `GET /records/{id}` — detalle de candidato
  - `POST /records` — crear candidato
  - `PUT /records/{id}` — actualizar candidato
  - `PATCH /records/{id}` — actualización parcial (status/stage)
  - `GET /records/{id}/notes` — listar notas
  - `POST /records/{id}/notes` — crear nota
  - `DELETE /records/{id}/notes/{noteId}` — eliminar nota
- **BFF del backoffice implementado:** `uis/backoffice/app/api/[...path]/route.ts` reenvía `GET`, `POST`, `PUT`, `PATCH` y `DELETE` de `/api/<ruta>` a la variable de servidor `API_BASE_URL` (`http://localhost:8000/api/v1`) sin lógica. Copia `Content-Type`, `Accept` y `Authorization`. Responde 500 `api_not_configured` si falta la variable y 502 `api_unavailable` si la API no responde. El tracker no lo usa: llama a la API de playground y no recibe el token.
- **Sesión en el backoffice (ticket AUTH-02, rama `feature/auth-frontend`, completada; divergencias en `docs/BRIEFING_DIVERGENCES.md`):**
  - **Token:** JWT en `localStorage` (`lib/auth/token.ts`, clave `brasaland.access_token`), con un evento propio para la pestaña actual y `storage` para las demás.
  - **`lib/api-client.ts`:** `apiFetch`/`apiJson` añaden `Authorization: Bearer` y convierten los errores en `ApiError` (`status`, `code`, `message`, `details`). Ante un 401, o un 403 `inactive_user`, borran el token y redirigen a `/login?next=&reason=`, salvo con `endSessionOnAuthError: false` (login y registro).
  - **Rutas:** grupos `app/(protegido)/` (portada y herramientas) y `app/(publico)/` (`/login`, `/register`); las URL no cambian. El layout protegido usa `SessionProvider`, un guard en el cliente: sin token redirige y con token valida con `GET /auth/me` antes de mostrar nada. `ProtectedShell` y `AccountMenu` completan la cabecera; `useSession()` da acceso al usuario.
  - **Sin `proxy.ts`:** el servidor no puede leer `localStorage`.
  - **Recuperación de contraseña (AUTH-03, rama `feature/password-reset`):** `/forgot-password` y `/reset-password` en `(publico)`. `/reset-password` comprueba el enlace al abrirse y declara `referrer: no-referrer`. `lib/auth/validation.ts` reúne las reglas de contraseña (`passwordError`, `validateNewPassword`) y `mergeFieldErrors`. Pendiente: `/account/change-password`.
  - **Perfil:** `/account/profile` (`components/account/`) usa el usuario de `useSession()` y guarda con `PUT /profiles/me`, enviando solo los campos cambiados (vacío → `null`). Después actualiza la sesión con `setUser`.
- **Sigue pendiente:** la base de datos definitiva (TinyDB es provisional) y el resto de dominios. El website leerá locales y menú desde el servidor y el alta de Brasa Points se conectará a `POST /loyalty/enrollments`. No describir estas integraciones como implementadas.

### Paquetes Compartidos

- **`@repo/shared-types`** (`packages/shared/`) — tipos base compartidos (`Id`, `BaseEntity`) para uso transversal entre proyectos. Aún sin consumidores.
- **`@repo/brasa-core`** (`packages/brasa-core/`) — modelos y lógica de negocio de Brasaland. Paquete transitorio; lo consume `uis/backoffice`.
- La refactorización de `uis/` consolidó el Talent Pipeline Tracker y `/funciones` como herramientas de `uis/backoffice`; `uis/website` sigue siendo una aplicación independiente. El backoffice no comparte layout con el website.
- **Website:** `/` es la landing y `/registro` el formulario de Brasa Points. `lib/locations.ts` contiene datos de ejemplo y `lib/api.ts` simula el envío; ambas integraciones se sustituirán cuando exista el backend.

### Utilidades Core (`packages/brasa-core/`)

- **Transitorio:** el backend será la fuente de verdad de las reglas de negocio. El paquete no admite reglas ni consumidores nuevos, sirve de referencia para portar la lógica a Python y se eliminará cuando deje de usarse.
- **TypeScript** sin compilar: `uis/backoffice` lo enlaza con una dependencia `file:`, `transpilePackages` y `turbopack.root` en la raíz del repositorio.
- Módulos:
  - `types/models.ts` — modelos de dominio de Brasaland (`MenuItem`, `Location`, `SaleTransaction`, `WasteRecord`, `CountryMetrics`, etc.)
  - `utils/collections.ts` — filtros y ordenamiento (por locación, fechas, categoría, precio, capacidad)
  - `utils/search.ts` — búsqueda por ID, nombre (case-insensitive), búsqueda binaria
  - `utils/transformations.ts` — cálculos financieros, margen de ganancia, scoring de rendimiento, ranking, ticket promedio, métricas por país
  - `utils/validations.ts` — validación de MenuItem, SaleTransaction, Location
  - `utils/test-data.ts` — datos de ejemplo (válidos e inválidos)

### Agentes / IA

- **Python** (esqueleto vacío en `agents/_template/agent.py`)
- Estructura de directorios: `agents/`, `skills/`, `mcps/`, `workflows/`

### Infraestructura y Datos

- `infra/`, `internal/` — solo READMEs, sin implementación.
- `scripts/incident-report/` — procesador de reportes de incidentes en **Python 3**, solo con la librería estándar (`csv`, `decimal`) y pruebas con `unittest`. Lee de `data/raw/` y exporta a `data/process/results.csv`.
- `data/` — estructura por etapas: `raw/`, `process/`, `pipelines/`, `eval/`. `raw/` contiene `incidents-brasaland.csv`; el resto solo tiene READMEs.

---

## Decisiones de Arquitectura

### 1. Estructura Monorepo por Capas

Basada en el template oficial de 4Geeks Academy. Cada carpeta de primer nivel tiene una responsabilidad única:

| Capa | Carpetas | Responsabilidad |
|---|---|---|
| Contexto de negocio | `CONTEXT.md` | Hechos de dominio, restricciones de la empresa asignada |
| Interfaces de usuario | `uis/`, `services/` | Frontends y backends |
| Datos | `data/` | Archivos fuente, pipelines, datasets procesados |
| IA | `agents/`, `skills/`, `mcps/` | Agentes, capacidades reutilizables, servidores MCP |
| Automatización | `workflows/` | Flujos n8n y orquestación entre sistemas |
| Reutilización | `packages/`, `shared/` | Tipos compartidos, SDKs, esquemas |
| Operaciones | `infra/`, `scripts/`, `internal/` | Docker, configs de deploy, scripts internos |
| Documentación | `docs/` | Arquitectura, decisiones, convenciones |

### 1.1 Ubicación de frontends y backend

| Ruta | Qué va aquí cuando se cree |
|---|---|
| `uis/` | Proyectos frontend de la empresa. |
| `uis/website/` | Web corporativa de cara al público (ruta `/`, marca y texto alineados con `CONTEXT.md`). |
| `uis/backoffice/` | App interna de la empresa, con layout propio y separado del sitio público (vista de entrada en `/`). |
| `services/` | APIs y servicios backend. |

**Estado actual:** `uis/website/` y `uis/backoffice/` existen como proyectos Next.js independientes. El Talent Pipeline Tracker es un módulo de `uis/backoffice/`, en `/talento`. Cada herramienta interna nueva se registra en `uis/backoffice/lib/tools.ts`, y eso incluye la formación y el resto de áreas internas. Con la autenticación, esa lista se filtrará por permisos con `GET /auth/me`; la autorización real vive en la API.

La integración mediante BFF, el filtrado de herramientas por permisos y las lecturas dinámicas del website son decisiones futuras de `docs/ARCHITECTURE_PROPOSAL.md`, no comportamiento actualmente implementado.

### 2. Backend Centralizado (Recomendación)

El template recomienda **un único backend FastAPI** en lugar de microservicios. Los endpoints se organizan por módulos/dominios (locations, menus, sales, telemetry, etc.). Solo se deben extraer workers cuando sea estrictamente necesario.

### 3. Next.js App Router con React 19

El frontend usa el App Router de Next.js 16 con:
- Componentes del lado del servidor por defecto
- `"use client"` para interactividad (manejo de estado, efectos, hooks de router)
- Layout anidado con Header global
- Sistema de rutas dinámicas (`/talento/candidates/[id]`)

### 4. Tipos de Dominio de Brasaland

Los modelos de datos están diseñados específicamente para el dominio de Brasaland:
- Precios en dos monedas (USD y COP) con tasa de conversión fija (1 USD = 4000 COP)
- Locaciones con país, ciudad, capacidad, costos operativos
- Ventas con método de pago, mesero, cantidad
- Desperdicio con categorías de razón
- Scoring de rendimiento multi-factor (ingresos, eficiencia, desperdicio, margen)

### 5. Pruebas Manuales de Funciones

La herramienta `/funciones` de `uis/backoffice` ejecuta las utilidades de `@repo/brasa-core` (filtros, búsqueda, reportes, validaciones) con datos de ejemplo mediante `lib/funciones/runner.ts`. Es temporal: cuando las reglas pasen al backend, debe retirarse o llamar a la API.

### 6. Validación de Datos Separada

Las reglas de validación de negocio (para MenuItem, SaleTransaction, Location) viven en módulos independientes (`packages/brasa-core/utils/validations.ts`) y devuelven objetos `{ valid, errors[] }`.

### 7. ESLint con Configuración de Next.js

Se usa `eslint-config-next` con las variantes `core-web-vitals` y `typescript`, ignorando `.next/`, `out/`, `build/`, `next-env.d.ts`.

---

## Restricciones Técnicas

### Lenguaje y Compilación

- **TypeScript estricto** (`strict: true`) en todos los tsconfig.
- **Target ES2017** para los proyectos Next.js, que también compilan `@repo/brasa-core`.
- **moduleResolution "bundler"** en Next.js.
- Sin transpilador configurado a nivel raíz (cada proyecto maneja su propia compilación).

### Frontend

- Tailwind CSS v4 usa la sintaxis `@import "tailwindcss"` (sin `@tailwind` directives).
- PostCSS configurado con el plugin `@tailwindcss/postcss`.
- Los hooks personalizados incluyen: `useAutoClose`, `useEscapeKey`, `useNotes`, `usePatchField`.
- El path alias `@/*` resuelve desde la raíz del proyecto UI.

### Conversión de Moneda

- Tasa fija: **1 USD = 4000 COP**. No hay manejo de tasas variables ni conexión a APIs de tipo de cambio.

### Modelos de Datos

- `MenuItem`: precio base y costo de ingredientes en USD/COP, `prepTimeMinutes` entre 1 y 60, disponible en al menos un país.
- `Location`: `openingYear >= 2008`, `seatingCapacity > 0`, `staffCount > 0`.
- `SaleTransaction`: `quantity > 0`, `waiterName` no vacío, ambos precios > 0.
- `WasteRecord`: cantidad > 0, costo > 0, razón no vacía.

### Backend

- Existen los dominios `incidents` y `suppliers` de `services/brasaland-api/`. El último análisis de incidentes vive en memoria y se pierde al reiniciar. Los proveedores persisten en TinyDB, que es provisional hasta Postgres con ORM y no está pensado para muchos procesos escribiendo a la vez.
- El tracker sigue usando la API de playground (ver sección de Stack → Backend).
- La autenticación JWT protege todas las rutas salvo login, registro y `/health` (rama `feature/auth-api`). No hay permisos por rol fuera de la gestión de usuarios. El backoffice envía el token a través del BFF (rama `feature/auth-frontend`).

### Agentes / IA

- Solo existe el esqueleto del template (`agents/_template/agent.py` vacío).
- No hay agentes, skills, MCP servers ni workflows implementados aún.
- No hay integración con modelos de lenguaje (LLMs) ni frameworks de agentes.

### Infraestructura

- Sin Docker, docker-compose, CI/CD, o scripts de deploy.
- Sin base de datos de servidor; solo los archivos TinyDB locales de `suppliers` y de usuarios y perfiles.
- Sin configuración de hosting/cloud.

### Datos

- El único dataset es `data/raw/incidents-brasaland.csv`, que se conserva sin modificar. Los demás datos de ejemplo existen solo en TypeScript (`packages/brasa-core/utils/test-data.ts`), sin persistencia.
- Los artefactos generados en `data/process/` (como `results.csv`) no se versionan.

### Dependencias Externas

- **Node.js**: requerido para el frontend Next.js.
- **Python 3**: requerido para `services/brasaland-api/` (≥ 3.11, con su `.venv`, gestionado con **uv**; en Windows `winget install --id astral-sh.uv -e`), para `scripts/incident-report/` (sin dependencias; importa el servicio del backend) y para agentes (esqueleto).
- Sin gestor de monorepo configurado a nivel raíz (no hay `package.json` raíz, ni turborepo, ni nx, ni lerna).

---

_Actualizado: 2026-11-06_