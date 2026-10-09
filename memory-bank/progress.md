# Progress

## Estado Actual del Desarrollo

### 1. Contexto y Configuración Inicial

| Elemento | Estado |
|---|---|
| `CONTEXT.md` — Briefing de Brasaland | ✅ Completado |
| `company-choice.md` — Selección de empresa y enfoque personal | ✅ Completado |
| `memory-bank/projectbrief.md` — Descripción del negocio, problema y objetivos | ✅ Completado |
| `memory-bank/techContext.md` — Stack tecnológico, decisiones de arquitectura, restricciones | ✅ Completado |
| `memory-bank/progress.md` — Este archivo | ✅ Completado |
| `AGENTS.md` raíz | ❌ Pendiente |

### 2. Frontend — Talent Pipeline Tracker (`uis/talent-pipeline-tracker/`)

Aplicación Next.js 16 con App Router para el seguimiento de candidatos del proceso de selección de Brasaland.

| Componente | Estado |
|---|---|
| **Página principal** (`app/page.tsx`) — listado de candidatos con filtros | ✅ Implementado |
| **Detalle de candidato** (`app/candidates/[id]/page.tsx`) — vista individual | ✅ Implementado |
| **Header** global con navegación | ✅ Implementado |
| **CandidateCard** — tarjeta resumen con datos y badges | ✅ Implementado |
| **CandidateHeader** — cabecera con nombre y botón editar | ✅ Implementado |
| **CandidateDetails** — datos completos del candidato | ✅ Implementado |
| **FilterBar** — filtros por status, stage y búsqueda | ✅ Implementado |
| **StatusBadge / StageBadge** — badges visuales | ✅ Implementado |
| **StatusStageSelectors** — selects para cambiar status/stage | ✅ Implementado |
| **CandidateFormModal** — modal de creación/edición | ✅ Implementado |
| **NotesSection / NoteItem / NewNoteModal** — sección de notas | ✅ Implementado |
| **Modal / FormField / LabeledSelect** — componentes base reutilizables | ✅ Implementado |
| **BackLink / Button / Badge / ExternalLink** — componentes atómicos | ✅ Implementado |
| **EmptyMessage / ErrorMessage / LoadingMessage** — estados de UI | ✅ Implementado |
| **DetailItem** — fila de detalle genérica | ✅ Implementado |
| **Tipos (`types/record.ts`)** — interfaces de Record, Note, API responses | ✅ Implementado |
| **API client (`lib/api.ts`)** — fetch a backend REST con filtros | ✅ Implementado |
| **Hooks** (`useAutoClose`, `useEscapeKey`, `useNotes`, `usePatchField`) | ✅ Implementado |
| **Formato (`lib/format.ts`)** — formatDate, formatDateTime | ✅ Implementado |

**Backend:** La UI está lista pero no hay backend real. Los datos se obtendrían de una API REST aún no implementada.

### 3. Utilidades Core TypeScript (`src/`)

Módulos completos con modelos de dominio, lógica de negocio y validaciones específicas de Brasaland.

| Módulo | Estado |
|---|---|
| `types/models.ts` — Modelos de dominio (MenuItem, Location, SaleTransaction, WasteRecord, CountryMetrics, etc.) | ✅ Completado |
| `utils/collections.ts` — Filtros y ordenamiento (por local, fecha, categoría, precio, capacidad) | ✅ Completado |
| `utils/search.ts` — Búsqueda por ID, nombre (case-insensitive), búsqueda binaria | ✅ Completado |
| `utils/transformations.ts` — Cálculos financieros, scoring, ranking, ticket promedio, métricas por país | ✅ Completado |
| `utils/validations.ts` — Validaciones de dominio con formato `{ valid, errors[] }` | ✅ Completado |
| `utils/test-data.ts` — Datos de ejemplo (válidos e inválidos para pruebas) | ✅ Completado |
| `utils/manual-runner.ts` — API `brasaManual` expuesta en `window` para consola del navegador | ✅ Completado |

### 4. Backend / Servicios

| Elemento | Estado |
|---|---|
| `services/` — carpeta preparada | ❌ Vacío (solo READMEs) |
| API REST (FastAPI recomendado) | ❌ No iniciado |
| Base de datos | ❌ No definida |
| Autenticación / Autorización | ❌ No iniciado |

### 5. Agentes / IA

| Elemento | Estado |
|---|---|
| `agents/_template/agent.py` — esqueleto | ⬜️ Vacío (solo archivo creado) |
| `agents/tools/` — carpeta preparada | ❌ Vacío |
| `skills/` — carpeta con ejemplos (data-analysis, code-review, research) | ⬜️ Solo scripts de ejemplo |
| `mcps/` — carpeta preparada | ❌ Vacío |
| `workflows/` — carpeta preparada | ❌ Vacío |

### 6. Website Corporativo

| Elemento | Estado |
|---|---|
| `website/index.html` — Página principal | ✅ Implementado |
| `website/funciones-brasaland.html` — Página de funciones | ✅ Implementado |
| `website/application.html` — Página de aplicación | ✅ Implementado |
| `website/validation.js` — Script de validación | ✅ Implementado |
| `website/manual-tests.js` — Pruebas manuales | ✅ Implementado |
| `website/media/` — Recursos multimedia | ✅ Con contenido |

### 7. Paquetes Compartidos

| Elemento | Estado |
|---|---|
| `packages/shared/` — `@repo/shared-types` (Id, BaseEntity) | ✅ Setup inicial |
| Sin gestor de monorepo raíz (turborepo/nx/lerna) | ❌ No configurado |

### 8. Datos

| Elemento | Estado |
|---|---|
| `data/raw/` — datos fuente | ❌ Vacío |
| `data/process/` — datos procesados | ❌ Vacío |
| `data/pipelines/` — pipelines ETL | ❌ Vacío |
| `data/eval/` — datasets de evaluación | ❌ Vacío |

### 9. Infraestructura

| Elemento | Estado |
|---|---|
| `infra/` — Docker, deploy | ❌ No iniciado |
| `scripts/` — scripts auxiliares | ❌ No iniciado |
| `internal/` — CLIs internos | ❌ No iniciado |

---

## Propuesta de Próximos Pasos

### Inmediatos (Sprint Actual)

1. **AGENTS.md raíz** — Crear el archivo de directrices para agentes de IA en el proyecto, definiendo:
   - Convenciones de código y estilo.
   - Instrucciones sobre qué herramientas usar y cómo.
   - Reglas para la generación y modificación de código.
   - Referencia a los skills disponibles y cómo invocarlos.

2. **Primer skill en `skills/`** — Implementar al menos un skill funcional directamente relacionado con el dominio de Brasaland, por ejemplo:
   - **Skill de recetario interactivo** — capaz de buscar recetas por nombre, filtrar por ingredientes, convertir unidades y ajustar porciones.
   - **Skill de análisis de ventas** — procesar datos de ventas, calcular métricas y generar reportes.
   - **Skill de validación de datos** — verificar integridad y consistencia de datos de locales, menús y ventas.

3. **(Opcional) Primer agente en `agents/`** — Si el skill lo requiere, crear un agente básico que lo utilice.

### Corto Plazo (Próximos Sprints)

4. **Backend FastAPI** — Implementar la API central de Brasaland:
   - Modelos de base de datos.
   - Endpoints REST para locales, menús, ventas.
   - Conexión con el frontend existente (talent-pipeline-tracker).
   - Desplegar en entorno local con Docker.

5. **Migración de utilidades core** — Refactorizar `src/` (TypeScript) a Python si la lógica de negocio debe residir en el backend, o mantener como librería frontend independiente si el backend la reimplementa.

6. **Pipeline de datos** — Poblar `data/` con datasets realistas de Brasaland y crear pipelines ETL básicos.

### Mediano Plazo

7. **Agente de formación y recetario** — Desarrollar el agente principal enfocado en el área de Formación y Estándares de Calidad (prioridad personal del proyecto), integrando el skill del paso 2.

8. **Sistema de fidelización** — Implementar el módulo de "Brasa Points" digital con CRM de clientes.

9. **Dashboard operativo** — Tablero en tiempo real para Operaciones de Restaurante con alertas inteligentes.

10. **Workflows de automatización** — Flujos n8n para orquestación de procesos cross-sistema (ej. notificaciones, reportes semanales).

---

## Riesgos y Bloqueantes

- **Backend ausente**: el frontend está desacoplado pero no puede validarse end-to-end sin backend.
- **Sin base de datos definida**: no hay decisión tomada sobre SQL vs NoSQL ni esquema de datos.
- **Dependencia de Python para agentes**: el esqueleto está en Python, pero el resto del stack es TypeScript/JavaScript — se debe decidir si los agentes serán Python puro o se integran vía MCP/subprocess.
- **Sin gestor de monorepo**: no hay `package.json` raíz ni scripts compartidos; cada proyecto se gestiona independientemente.

---

_Actualizado: 2026-10-09_