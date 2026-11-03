# Progress

## Estado Actual del Desarrollo

La refactorización de las interfaces está completada: `uis/website` y `uis/backoffice` son aplicaciones Next.js independientes; el tracker y las pruebas de funciones viven como herramientas del backoffice. Las decisiones posteriores de arquitectura del backend están documentadas como propuesta y no implican que el backend o la autenticación estén implementados.

El procesador de reportes de incidentes (`scripts/incident-report/`) está completado: valida y resume el CSV de incidentes de Operaciones, coincide exactamente con los valores esperados del briefing y exporta las métricas a `data/process/results.csv`.

**Fase 2 completada (integración en la plataforma):** `services/brasaland-api/` (FastAPI) implementa el dominio `incidents` con `POST /api/v1/incidents/analyze` y `GET /api/v1/incidents/results/export`, con errores HTTP apropiados y 24 pruebas pytest. La lógica se extrajo del script a `app/domains/incidents/service.py`, que es su fuente de verdad, y el script la importa. En el backoffice, la herramienta `/incidencias` sube el CSV (arrastrando o con el selector), muestra el resumen y los registros inválidos con su motivo, y descarga `results.csv`. Llama a la API a través del intermediario BFF (`app/api/[...path]/route.ts`), configurado con `API_BASE_URL`. La revisión manual en el navegador está hecha y aprobada (2026-11-03).

**Directorio de proveedores (milestone 09) completado en la rama `directorio-prov`**, que parte de `features/csv-reader` (PR abierto):

- **Backend:** el dominio `suppliers` de `services/brasaland-api/` (FastAPI + TinyDB + Pydantic) tiene `POST/GET /api/v1/suppliers`, `GET/DELETE /suppliers/{id}` y `PATCH /suppliers/{id}/rate` y `/status`.
- **Datos:** el seeder (`uv run seed`) es idempotente, y la API siembra al arrancar si la base está vacía. Los datos persisten en `storage/brasaland-db.json`.
- **Frontend:** la herramienta `/proveedores` del backoffice permite filtrar, dar de alta, actualizar la tarifa y activar o suspender.
- **Verificación:** 132 pruebas pytest pasan. La revisión en el navegador está hecha (2026-11-03).
- **Herramientas:** el servicio adopta uv (`uv.lock` versionado).

### 1. Contexto y Configuración Inicial

| Elemento | Estado |
|---|---|
| `CONTEXT.md` — Briefing de Brasaland | ✅ Completado |
| `company-choice.md` — Selección de empresa y enfoque personal | ✅ Completado |
| `memory-bank/projectbrief.md` — Descripción del negocio, problema y objetivos | ✅ Completado |
| `memory-bank/techContext.md` — Stack tecnológico, decisiones de arquitectura, restricciones | ✅ Completado |
| `memory-bank/progress.md` — Este archivo | ✅ Completado |
| `AGENTS.md` raíz | ✅ Completado |
| `.agents/rules/` — reglas de desarrollo (`brasaland-domain`, `monorepo-structure`) | ✅ Completado |
| `.agents/skills/` — skills de desarrollo (`update-memory-bank`, `new-module-scaffold`, `validate-domain-model`) | ✅ Completado |

### 2. Backoffice (`uis/backoffice/`)

Aplicación interna Next.js 16 con App Router, en el puerto 3001. Reúne las herramientas del personal; cada herramienta nueva se añade con su carpeta en `app/` y una entrada en `lib/tools.ts`. La estructura unificada sustituye al tracker como aplicación independiente.

| Elemento | Estado |
|---|---|
| **Portada** (`app/page.tsx`) — una tarjeta por herramienta, generada desde `lib/tools.ts` | ✅ Implementado |
| **Header** global con navegación entre herramientas | ✅ Implementado |
| **Análisis de incidencias** (`app/incidencias/`) — carga del CSV con `FileDropzone`, resumen, registros inválidos y descarga de `results.csv` | ✅ Implementado; último análisis en la memoria de la API |
| **Directorio de proveedores** (`app/proveedores/`) — listado con badges de estado, filtros por país y categoría sin recargar, formulario de alta con validación y errores de la API, edición de tarifa y activar/suspender | ✅ Implementado; datos en el TinyDB de la API |
| **Pruebas de funciones** (`app/funciones/`) — filtros, búsquedas, reportes y validaciones con `@repo/brasa-core` | ✅ Implementado |
| **Autenticación** | ❌ No iniciado; no debe publicarse sin ella. `GET /auth/me` filtrará `lib/tools.ts` por permisos, con la autorización real en la API. La sesión y las llamadas a la API irán por un intermediario en Next.js |
| **Formación** | ❌ No iniciado; será una herramienta del backoffice, no una aplicación aparte |

**Intermediario (BFF)** (`app/api/[...path]/route.ts`): reenvía `GET`, `POST`, `PATCH` y `DELETE` de `/api/<ruta>` a `API_BASE_URL` (la API de Brasaland) sin lógica. ✅ Implementado; lo usan `/incidencias` y `/proveedores`.

**Talent Pipeline Tracker** (`app/talento/`): seguimiento de candidatos del proceso de selección de Brasaland. `/funciones` también está integrado como herramienta temporal para probar `@repo/brasa-core`.

| Componente | Estado |
|---|---|
| **Página principal** (`app/talento/page.tsx`) — listado de candidatos con filtros | ✅ Implementado |
| **Detalle de candidato** (`app/talento/candidates/[id]/page.tsx`) — vista individual | ✅ Implementado |
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
| **API client (`lib/talento/api.ts`)** — fetch a backend REST con filtros | ✅ Implementado |
| **Hooks** (`useAutoClose`, `useEscapeKey`, `useNotes`, `usePatchField`) | ✅ Implementado |
| **Formato (`lib/format.ts`)** — formatDate, formatDateTime | ✅ Implementado |

**Backend:** La UI está lista pero no hay backend real. Los datos se obtendrían de una API REST aún no implementada.

### 3. Utilidades Core TypeScript (`packages/brasa-core/`)

Paquete transitorio `@repo/brasa-core` con modelos de dominio, lógica de negocio y validaciones específicas de Brasaland. Lo consume `uis/backoffice` para `/funciones`. No admite reglas nuevas: el backend será la fuente de verdad.

| Módulo | Estado |
|---|---|
| `types/models.ts` — Modelos de dominio (MenuItem, Location, SaleTransaction, WasteRecord, CountryMetrics, etc.) | ✅ Completado |
| `utils/collections.ts` — Filtros y ordenamiento (por local, fecha, categoría, precio, capacidad) | ✅ Completado |
| `utils/search.ts` — Búsqueda por ID, nombre (case-insensitive), búsqueda binaria | ✅ Completado |
| `utils/transformations.ts` — Cálculos financieros, scoring, ranking, ticket promedio, métricas por país | ✅ Completado |
| `utils/validations.ts` — Validaciones de dominio con formato `{ valid, errors[] }` | ✅ Completado |
| `utils/test-data.ts` — Datos de ejemplo (válidos e inválidos para pruebas) | ✅ Completado |

### 4. Backend / Servicios

| Elemento | Estado |
|---|---|
| `services/brasaland-api/` — API FastAPI por dominios (propuesta de arquitectura) | ✅ Iniciada |
| Dominio `incidents` — `POST /api/v1/incidents/analyze`, `GET /api/v1/incidents/results/export`, `GET /health`; 24 pruebas pytest | ✅ Implementado; último análisis en memoria |
| Dominio `suppliers` — CRUD del directorio de proveedores, filtros `country`/`category`, `PATCH` de tarifa (registra `updated_at`) y de estado, 409 por nombre duplicado; seeder `uv run seed`; 108 pruebas pytest | ✅ Implementado; TinyDB en `storage/brasaland-db.json` |
| Resto de dominios (`auth`, `locations`, `recruitment`…) | ❌ No iniciado |
| Base de datos | ⏳ TinyDB provisional para `suppliers` (directiva del CTO); el motor definitivo (Postgres con ORM) está sin decidir |
| Autenticación / Autorización | ❌ No iniciado |

### 5. Agentes / IA

| Elemento | Estado |
|---|---|
| `agents/_template/agent.py` — esqueleto | ⬜️ Vacío (solo archivo creado) |
| `agents/tools/` — carpeta preparada | ❌ Vacío |
| `skills/` — carpeta con ejemplos (data-analysis, code-review, research) | ⬜️ Solo scripts de ejemplo |
| `mcps/` — carpeta preparada | ❌ Vacío |
| `workflows/` — carpeta preparada | ❌ Vacío |

### 6. Website Corporativo (`uis/website/`; las rutas de la tabla son relativas a esa carpeta)

Aplicación Next.js 16 con App Router, en el puerto 3000. Sustituye a las páginas HTML anteriores.

| Elemento | Estado |
|---|---|
| `app/page.tsx` — Landing | ✅ Implementado |
| `app/registro/page.tsx` — Formulario de Brasa Points en tres pasos | ✅ Implementado; envío simulado |
| `lib/locations.ts` — Países, ciudades y sedes (datos de ejemplo) | ✅ Implementado |
| `lib/registration-validation.ts` — Reglas de validación | ✅ Implementado |
| `public/media/` — Recursos multimedia | ✅ Con contenido |

### 7. Paquetes Compartidos

| Elemento | Estado |
|---|---|
| `packages/brasa-core/` — `@repo/brasa-core` (dominio y lógica de negocio) | ⏳ Transitorio; consumido por `uis/backoffice` |
| `packages/shared/` — `@repo/shared-types` (Id, BaseEntity) | ✅ Setup inicial; sin consumidores |
| Sin gestor de monorepo raíz (turborepo/nx/lerna) | ❌ No configurado |

### 8. Datos

| Elemento | Estado |
|---|---|
| `data/raw/` — datos fuente | ✅ `incidents-brasaland.csv` (100 incidentes de prueba, enero de 2024) |
| `data/process/` — datos procesados | ✅ `results.csv` generado por `scripts/incident-report/`; ignorado en Git |
| `data/pipelines/` — pipelines ETL | ❌ Vacío |
| `data/eval/` — datasets de evaluación | ❌ Vacío |

### 9. Infraestructura

| Elemento | Estado |
|---|---|
| `infra/` — Docker, deploy | ❌ No iniciado |
| `scripts/incident-report/` — procesador de reportes de incidentes (Python, sin dependencias, 32 pruebas `unittest`) | ✅ Implementado |
| `internal/` — CLIs internos | ❌ No iniciado |

---

## Propuesta de Próximos Pasos

### Inmediatos (Sprint Actual)

0. **Entregar el Directorio de proveedores (milestone 09)** — Implementado y revisado en la rama `directorio-prov`. La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Directorio de proveedores"): `services/brasaland-api/` en lugar de `services/api/`, `/api/v1/suppliers`, `/proveedores` en el backoffice y las decisiones de funcionamiento. Cuando se fusione `features/csv-reader`, el PR de esta rama debe apuntar a `main`.

0. **Entregar la Fase 2 del procesador de incidentes** — La implementación está revisada y aprobada. Queda la entrega, que debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md`: rutas y carpetas, lógica compartida dentro de la API y no en `packages/`, diferencias con la salida del briefing y decisiones de funcionamiento.

1. ✅ **AGENTS.md raíz** — Completado (junto con `.agents/rules/` y `.agents/skills/`). Define:
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

4. **Backend FastAPI** — Seguir con la API central de Brasaland (`services/brasaland-api/`, ya iniciada con `incidents`):
   - Modelos de base de datos.
   - Endpoints REST para locales, menús, ventas.
   - Conexión con el Talent Pipeline Tracker (`uis/backoffice`), a través de un intermediario en Next.js.
   - Lectura de sedes y menú desde el servidor de Next.js en `uis/website`, sustituyendo `lib/locations.ts`. El formulario pasará a enviar `location_id` (UUID) y el país en ISO 3166-1 alfa-2 (`CO`, `US`).
   - Alta pública de Brasa Points (`POST /loyalty/enrollments`), llamada desde el navegador, para sustituir el envío simulado del formulario. Es solo registro, sin credenciales, con límite de peticiones, respuesta neutra, registro del consentimiento y confirmación del correo.
   - Desplegar en entorno local con Docker.

5. **Migración de utilidades core** — Portar a Python, dominio por dominio, las reglas de `packages/brasa-core`. Decisión tomada: el backend es la fuente de verdad. Al terminar, retirar `/funciones` o hacer que llame a la API, y eliminar el paquete junto con su configuración en `uis/backoffice`.

6. **Pipeline de datos** — Poblar `data/` con datasets realistas de Brasaland y crear pipelines ETL básicos. Ya hay un primer dataset (`data/raw/incidents-brasaland.csv`) con su procesador en `scripts/incident-report/`; sus reglas de validación servirán de referencia para la ingesta de incidentes del dashboard operativo.

### Mediano Plazo

7. **Agente de formación y recetario** — Desarrollar el agente principal enfocado en el área de Formación y Estándares de Calidad (prioridad personal del proyecto), integrando el skill del paso 2.

8. **Sistema de fidelización** — Implementar el módulo de "Brasa Points" digital con CRM de clientes.

9. **Dashboard operativo** — Tablero en tiempo real para Operaciones de Restaurante con alertas inteligentes.

10. **Workflows de automatización** — Flujos n8n para orquestación de procesos cross-sistema (ej. notificaciones, reportes semanales).

---

## Riesgos y Bloqueantes

- **Backend incipiente**: solo existen los dominios `incidents` (su último análisis vive en memoria) y `suppliers` (TinyDB provisional), sin autenticación. El tracker sigue usando la API de playground.
- **Sin base de datos definitiva**: TinyDB es provisional y solo para `suppliers`. Falta decidir el motor (el CTO apunta a Postgres con ORM), las migraciones y el esquema. TinyDB no está pensado para muchos procesos escribiendo a la vez.
- **`suppliers` frente a `procurement`**: la propuesta reservaba los proveedores para `procurement/`. Cuando se aborden el historial de precios y las compras, hay que integrar ambos dominios para que solo uno sea dueño de los proveedores (propuesta, 2.7).
- **Dependencia de Python para agentes**: el esqueleto está en Python, pero el resto del stack es TypeScript/JavaScript — se debe decidir si los agentes serán Python puro o se integran vía MCP/subprocess.
- **Sin gestor de monorepo**: no hay `package.json` raíz ni scripts compartidos; cada proyecto se gestiona independientemente.
- **Website no publicable aún**: el envío del formulario es simulado, faltan los términos del programa y las sedes usan datos de ejemplo. El detalle está en `uis/website/README.es.md`.
- **Backoffice sin autenticación**: no debe publicarse hasta que exista el login.
- **Dependencia temporal del backoffice**: mientras exista `packages/brasa-core`, se construye desde la raíz del repositorio, y los cambios en el paquete también deben comprobar `uis/backoffice`.

---

_Actualizado: 2026-11-03_