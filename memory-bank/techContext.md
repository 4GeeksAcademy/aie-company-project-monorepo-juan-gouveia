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
- `uis/backoffice` (puerto 3001) — Herramientas internas: Talent Pipeline Tracker (`/talento`), pruebas de funciones (`/funciones`) y análisis de incidencias (`/incidencias`), que llama a la API de Brasaland a través del BFF.

### Backend / Servicios

- **`services/brasaland-api/`** — API central en **FastAPI** (Python ≥ 3.11, Pydantic 2), con la estructura por dominios de la propuesta de arquitectura. Dependencias en `pyproject.toml` (`fastapi`, `uvicorn[standard]`, `python-multipart`; de desarrollo, `pytest` y `httpx`) y entorno virtual propio en `.venv/`, ignorado en Git. Se arranca con `uvicorn app.main:app --port 8000`.
- **Único dominio implementado: `incidents`.** `POST /api/v1/incidents/analyze` (multipart, campo `file`) y `GET /api/v1/incidents/results/export` (`text/csv`, adjunto `results.csv`), más `GET /health`. `service.py` es la fuente de verdad de las reglas y solo usa la librería estándar, porque también lo importa `scripts/incident-report/analyze.py`. El último análisis se guarda en memoria (`repository.py`).
- **Errores:** formato único `{"error": {"code", "message"}}` (`app/core/errors.py`), con mensajes en español: 400 `missing_file` / `empty_file`, 413 `file_too_large` (5 MB), 415 `unsupported_file_type` (por extensión), 422 `invalid_encoding` / `missing_columns` / `no_records` / `invalid_request`, 404 `no_analysis` / `not_found`.
- **Desviación de la consigna, a justificar en la entrega:** se usan `services/brasaland-api/` y `/api/v1` (propuesta) en vez de `/services/api` y `/api/incidents/...`.
- El tracker consume actualmente una API REST de playground mediante `NEXT_PUBLIC_API_BASE_URL` con endpoints:
  - `GET /records` — listar candidatos (filtrable por status, stage, search)
  - `GET /records/{id}` — detalle de candidato
  - `POST /records` — crear candidato
  - `PUT /records/{id}` — actualizar candidato
  - `PATCH /records/{id}` — actualización parcial (status/stage)
  - `GET /records/{id}/notes` — listar notas
  - `POST /records/{id}/notes` — crear nota
  - `DELETE /records/{id}/notes/{noteId}` — eliminar nota
- **BFF del backoffice implementado:** `uis/backoffice/app/api/[...path]/route.ts` reenvía `/api/<ruta>` a la variable de servidor `API_BASE_URL` (`http://localhost:8000/api/v1`) sin lógica ni token (aún no hay autenticación). Responde 500 `api_not_configured` si falta la variable y 502 `api_unavailable` si la API no responde. El tracker no lo usa todavía.
- **Sigue pendiente:** autenticación, base de datos y el resto de dominios. El website leerá locales y menú desde el servidor y el alta de Brasa Points se conectará a `POST /loyalty/enrollments`. No describir estas integraciones como implementadas.

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

- Solo existe el dominio `incidents` de `services/brasaland-api/`. No hay modelos de BD ni configuración de base de datos; el último análisis vive en memoria y se pierde al reiniciar.
- El tracker sigue usando la API de playground (ver sección de Stack → Backend).
- No hay autenticación ni autorización implementadas.

### Agentes / IA

- Solo existe el esqueleto del template (`agents/_template/agent.py` vacío).
- No hay agentes, skills, MCP servers ni workflows implementados aún.
- No hay integración con modelos de lenguaje (LLMs) ni frameworks de agentes.

### Infraestructura

- Sin Docker, docker-compose, CI/CD, o scripts de deploy.
- Sin configuración de base de datos.
- Sin configuración de hosting/cloud.

### Datos

- El único dataset es `data/raw/incidents-brasaland.csv`, que se conserva sin modificar. Los demás datos de ejemplo existen solo en TypeScript (`packages/brasa-core/utils/test-data.ts`), sin persistencia.
- Los artefactos generados en `data/process/` (como `results.csv`) no se versionan.

### Dependencias Externas

- **Node.js**: requerido para el frontend Next.js.
- **Python 3**: requerido para `services/brasaland-api/` (≥ 3.11, con su `.venv`), para `scripts/incident-report/` (sin dependencias; importa el servicio del backend) y para agentes (esqueleto).
- Sin gestor de monorepo configurado a nivel raíz (no hay `package.json` raíz, ni turborepo, ni nx, ni lerna).

---

_Actualizado: 2026-11-02_