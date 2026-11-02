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
- `uis/backoffice` (puerto 3001) — Herramientas internas: Talent Pipeline Tracker (`/talento`) y pruebas de funciones (`/funciones`).

### Backend / Servicios

- **No implementado aún.** La carpeta `services/` contiene solo READMEs. La recomendación del template es usar **FastAPI** como backend centralizado.
- El frontend espera una API REST definida mediante `NEXT_PUBLIC_API_BASE_URL` con endpoints:
  - `GET /records` — listar candidatos (filtrable por status, stage, search)
  - `GET /records/{id}` — detalle de candidato
  - `POST /records` — crear candidato
  - `PUT /records/{id}` — actualizar candidato
  - `PATCH /records/{id}` — actualización parcial (status/stage)
  - `GET /records/{id}/notes` — listar notas
  - `POST /records/{id}/notes` — crear nota
  - `DELETE /records/{id}/notes/{noteId}` — eliminar nota

### Paquetes Compartidos

- **`@repo/shared-types`** (`packages/shared/`) — tipos base compartidos (`Id`, `BaseEntity`) para uso transversal entre proyectos. Aún sin consumidores.
- **`@repo/brasa-core`** (`packages/brasa-core/`) — modelos y lógica de negocio de Brasaland. Paquete transitorio; lo consume `uis/backoffice`.

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

- `infra/`, `scripts/`, `internal/` — solo READMEs, sin implementación.
- `data/` — estructura por etapas: `raw/`, `process/`, `pipelines/`, `eval/` (solo READMEs).

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

- **No implementado.** No hay servicios, controladores, modelos de BD ni configuración de base de datos.
- La UI asume un backend RESTful con endpoints específicos (ver sección de Stack → Backend).
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

- La carpeta `data/` está estructurada pero vacía (solo READMEs).
- Los datos de ejemplo existen únicamente en TypeScript (`packages/brasa-core/utils/test-data.ts`), no persistentes.

### Dependencias Externas

- **Node.js**: requerido para el frontend Next.js.
- **Python**: requerido para agentes (esqueleto).
- Sin gestor de monorepo configurado a nivel raíz (no hay `package.json` raíz, ni turborepo, ni nx, ni lerna).

---

_Actualizado: 2026-10-30_