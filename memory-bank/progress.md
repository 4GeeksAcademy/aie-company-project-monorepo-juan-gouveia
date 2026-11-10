# Progress

## Estado Actual del Desarrollo

La refactorización de las interfaces está completada: `uis/website` y `uis/backoffice` son aplicaciones Next.js independientes; el tracker y las pruebas de funciones viven como herramientas del backoffice. Las decisiones posteriores de arquitectura del backend están documentadas como propuesta; solo están implementados los dominios que se describen abajo (`incidents`, `suppliers` y la autenticación de la API).

El procesador de reportes de incidentes (`scripts/incident-report/`) está completado: valida y resume el CSV de incidentes de Operaciones, coincide exactamente con los valores esperados del briefing y exporta las métricas a `data/process/results.csv`.

**Fase 2 completada (integración en la plataforma):** `services/brasaland-api/` (FastAPI) implementa el dominio `incidents` con `POST /api/v1/incidents/analyze` y `GET /api/v1/incidents/results/export`, con errores HTTP apropiados y 24 pruebas pytest. La lógica se extrajo del script a `app/domains/incidents/service.py`, que es su fuente de verdad, y el script la importa. En el backoffice, la herramienta `/incidencias` sube el CSV (arrastrando o con el selector), muestra el resumen y los registros inválidos con su motivo, y descarga `results.csv`. Llama a la API a través del intermediario BFF (`app/api/[...path]/route.ts`), configurado con `API_BASE_URL`. La revisión manual en el navegador está hecha y aprobada (2026-11-03). Fusionado en `main` con el PR #6 (`features/csv-reader`, 2026-11-08).

**Directorio de proveedores (milestone 09) completado y fusionado en `main`** con el PR #7 (`directorio-prov`, 2026-11-08), después del #6:

- **Backend:** el dominio `suppliers` de `services/brasaland-api/` (FastAPI + TinyDB + Pydantic) tiene `POST/GET /api/v1/suppliers`, `GET/DELETE /suppliers/{id}` y `PATCH /suppliers/{id}/rate` y `/status`.
- **Datos:** el seeder (`uv run seed`) es idempotente, y la API siembra al arrancar si la base está vacía. Los datos persisten en `storage/brasaland-db.json`.
- **Frontend:** la herramienta `/proveedores` del backoffice permite filtrar, dar de alta, actualizar la tarifa y activar o suspender.
- **Verificación:** 132 pruebas pytest pasan. La revisión en el navegador está hecha (2026-11-03).
- **Herramientas:** el servicio adopta uv (`uv.lock` versionado).

**Autenticación (ticket AUTH-01) completada en la rama `feature/auth-api`**, creada desde `directorio-prov` cuando sus PR seguían abiertos. Las 6 fases están hechas y la verificación en `/docs` está revisada (2026-11-04):

- **Configuración:** `SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` se leen del entorno (`.env`, ignorado; plantilla `.env.example`) y la API no arranca sin ellas. Se ejecuta con `uv run --env-file .env uvicorn ...`.
- **Dominios nuevos:** `users` (solo credenciales, roles `admin`/`manager`/`user`, contraseñas con bcrypt de libpass), `profiles` (nombre y contacto, uno a uno) y `auth` (login con JWT de python-jose, `GET /auth/me` y la dependencia `get_current_user`). Todo bajo `/api/v1`, en TinyDB (`storage/auth-db.json`).
- **Permisos:** cada usuario solo accede a su cuenta (403 si no); listar usuarios y cambiar `role` o `is_active` es solo de admin. El primer admin se crea con `uv run create-admin`.
- **Rutas protegidas:** todas salvo `POST /auth/login`, `POST /users` y `GET /health`, incluidas las 8 de `incidents` y `suppliers`. `/incidencias` y `/proveedores` del backoffice reciben 401 hasta que el BFF envíe el token, como prevé el briefing.
- **Verificación:** 361 pruebas pytest pasan; flujo y rutas protegidas probados en vivo con bases temporales.
- **Documentación:** los README del servicio, de `services/` y del backoffice, `docs/BRIEFING_DIVERGENCES.md` (sección "Autenticación y protección de rutas", con la tabla de verificación) y `docs/ARCHITECTURE_PROPOSAL.md` (2.3, 2.5, 2.7, 3.2, 3.3 y 7).
- **PR:** #8, abierto. Sigue apuntando a `directorio-prov`, ya fusionada; hay que cambiar su destino a `main` antes de borrar esa rama.

**Autenticación en el frontend (ticket AUTH-02) completada en la rama `feature/auth-frontend`**, creada desde `feature/auth-api` porque su PR sigue abierto. Las 6 fases (0 a 5) están hechas y revisadas por el desarrollador (2026-11-06):

- **Alcance:** solo `uis/backoffice`; el website público (Hito 1) no cambia. Las decisiones F-1 a F-8 están en `docs/_private/plan-auth-frontend.md`.
- **Token y llamadas:** el token se guarda en `localStorage`. `lib/api-client.ts` lo envía en `Authorization: Bearer` al BFF, que ahora reenvía esa cabecera y también `PUT`. Ante un 401 o un 403 `inactive_user`, borra el token y redirige a `/login?next=&reason=`. `proveedores` e `incidencias` lo usan, y vuelven a funcionar con sesión.
- **Vistas:** `/login` y `/register` (`POST /users` y después login, errores por campo, botón para mostrar la contraseña) en el grupo `app/(publico)/`. `/account/profile` (protegida) muestra el email y el perfil de `GET /auth/me` y edita nombre, teléfono y dirección con `PUT /profiles/me`.
- **Protección:** las demás vistas están en `app/(protegido)/`, cuyo layout es un guard en el cliente (`SessionProvider`). Sin token redirige; con token valida con `GET /auth/me` antes de mostrar nada, y sincroniza la sesión entre pestañas. La cabecera tiene "Mi perfil" y "Cerrar sesión".
- **Verificación:** `tsc`, `lint` y `build` pasan; 361 pruebas de la API pasan; el website no cambia. Los flujos del BFF se probaron en vivo con bases temporales, y los del navegador los revisó el desarrollador.
- **Documentación:** `docs/BRIEFING_DIVERGENCES.md` (sección "Autenticación en el frontend", con la tabla de verificación), `docs/ARCHITECTURE_PROPOSAL.md` (5.2: token en `localStorage` reenviado por el BFF) y los README.
- **Commit:** `fb35b8d`, hecho por el desarrollador.
- **PR:** #9, abierto, contra `feature/auth-api` mientras el #8 no se fusione.

**Recuperación y cambio de contraseña (ticket AUTH-03) completada en la rama `feature/password-reset`**, creada desde `feature/auth-frontend` (`fb35b8d`). Las 6 fases (0 a 5) están hechas y revisadas por el desarrollador (2026-11-06 y 2026-11-08):

- **Correo:** Resend (elegido frente a SendGrid: plan gratuito permanente, alta simple y funciona sin dominio propio enviando al email de la cuenta). SDK `resend`; la API key va en `RESEND_API_KEY` (`.env`). Sin ella, la API arranca pero no envía nada. Envío real comprobado por el desarrollador.
- **API:** `POST /auth/forgot-password` (siempre 200, envío en segundo plano, máximo 3 enlaces por cuenta y hora), `POST /auth/reset-password/validate` (comprueba el enlace sin usarlo), `POST /auth/reset-password` (400 si el enlace no es válido, caducó o se usó) y `POST /auth/change-password` (protegido, 400 si la contraseña actual es incorrecta, devuelve un token nuevo).
- **Token del enlace:** JWT con `purpose` y `jti`, más la tabla `password_resets` de un solo uso; caduca con `PASSWORD_RESET_EXPIRE_MINUTES` (15–60, por defecto 30). `password_changed_at` invalida las sesiones anteriores (401 `session_revoked`). Los tokens de acceso y de restablecimiento no se aceptan uno por otro.
- **Correcciones de paso:**
  - Colisión de `doc_id` de TinyDB entre procesos en `users`, `profiles` y `password_resets` (`app/core/storage.py`): `uv run create-admin` con la API arrancada hacía fallar el siguiente registro.
  - En `/login` y `/register`, un error de la API borrado tapaba el aviso local (`mergeFieldErrors`).
- **Frontend:** `/forgot-password`, `/reset-password` (comprueba el enlace al abrirse, sin `Referer`) y el enlace "¿Olvidaste tu contraseña?" en `/login`. `/account/change-password` (protegida, enlazada desde "Mi perfil") guarda el token nuevo que devuelve la API y muestra "Contraseña actualizada."; una contraseña actual incorrecta se marca en su campo.
- **Verificación:** 433 pruebas de la API; `tsc`, `lint` y `build` del backoffice; flujo completo con correo real revisado por el desarrollador. El cambio de contraseña se probó en vivo por el BFF (400, 422, 401, token nuevo y `session_revoked` del anterior) y lo revisó el desarrollador en el navegador. Sin claves en el código ni en el historial de Git.
- **Documentación:** `docs/BRIEFING_DIVERGENCES.md`, sección "Recuperación y cambio de contraseña": rutas `/api/v1`, Resend, endpoint `validate`, `password_changed_at`, 422 ante un email mal formado, opcionales, correcciones de `doc_id` (AUTH-01) y `mergeFieldErrors` (AUTH-02), y la tabla de los 12 criterios. README de la API y del backoffice.
- **Commits:** `e87121c` (fases 0-3) y `2906225` (fases 4 y 5), hechos por el desarrollador.
- **PR:** #10, abierto, contra `feature/auth-frontend` mientras el #9 no se fusione.

**Gestor de incidencias centralizado completado en la rama `feature/incident-manager`**, creada desde `feature/password-reset` (`2906225`) porque los PR de AUTH siguen abiertos. Commit `ccd09cc`; PR #11 abierto contra esa rama. Decisiones G-1 a G-13 aprobadas y las 5 fases hechas (2026-11-08); el formulario y el panel, revisados por el desarrollador en el navegador:

- **API:** `POST`, `GET` (filtros `status`, `origin`, `branch` y `category`), `GET /summary`, `GET /{id}` y `PATCH /{id}/status` bajo `/api/v1/incidents`, junto al analizador del CSV, que no cambia. Valores exactos del briefing, ciclo de vida `open → in_progress | discarded → …`, errores de validación con 400 en estas rutas (el resto de la API sigue con 422) y un 500 genérico para cualquier excepción no controlada en toda la API.
- **Datos:** tabla `incidents` en `storage/brasaland-db.json`, con un bloqueo por archivo compartido con proveedores, y `incident_seed_log` para que el seed no duplique registros.
- **Lógica compartida:** las reglas del CSV de incidentes pasaron de la API a `packages/shared/` (paquete Python `brasaland-shared`, solo librería estándar), como pide la consigna. La API lo instala como dependencia local con uv; el analizador y el seed lo importan sin instalar nada. Sin duplicación.
- **Seed:** `scripts/seed_incidents.py` carga el CSV histórico (96 válidos, 4 inválidos reportados en consola), aplica las transformaciones del briefing y es idempotente. Tras el seed, `/api/incidents/summary` da exactamente los totales esperados.
- **Formulario:** `/gestor-incidencias/nueva` en el backoffice ("Registrar incidencia" en el menú), con campos grandes para tablet, validación de obligatorios en el cliente, la sede resaltada si `origin = branch`, nombres de sede del briefing, indicador de carga y errores de la API junto a su campo. El intermediario corta a los 15 s (504) y los 5xx sin mensaje propio se muestran con un texto comprensible.
- **Panel:** `/gestor-incidencias` ("Gestor de incidencias" en el menú) con el resumen por estado, categoría, origen y sede, y el listado con filtros por `status`, `origin` y `branch`. Cada bloque carga y falla por su cuenta (con "Reintentar"); el listado distingue vacío y sin resultados; el cambio de estado es optimista, solo ofrece transiciones válidas y vuelve atrás con aviso si falla.
- **Verificación:** 539 pruebas pytest (106 nuevas), 32 del analizador y 16 del seed; `tsc`, `lint` y `build` del backoffice; alta, 400, 502, 504, filtros y transiciones probados en vivo por el intermediario.
- **Revisión en el navegador:** fases 3 y 4 probadas por el desarrollador (2026-11-08), incluida la reversión del estado con la API apagada. En tablet, la cabecera se comporta ahora como en móvil (enlaces a herramientas solo desde `xl`).
- **Documentación:** `docs/BRIEFING_DIVERGENCES.md`, sección "Gestor de incidencias centralizado" (rutas `/api/v1`, `incident_seed_log`, 400 solo en el gestor, `status` fijo, menú en móvil y tablet, decisiones y la tabla de los 21 criterios), y la divergencia 3 del analizador marcada como resuelta. `ARCHITECTURE_PROPOSAL.md` (cuarto bloque en 2.7 y `packages/shared` en 6.2) y los README.
- **Pendiente:** fusionar el PR #11 (tras el #10) y la entrega; los hace el desarrollador.

**Auditoría de gestión de errores completada en la rama `feature/error-handling-audit`**, creada desde `feature/incident-manager` (2026-11-09). Commit de cierre `d8f39c2`; PR #12 abierto contra `feature/incident-manager`. Se auditó todo el repositorio y se corrigieron los 29 hallazgos (1 crítico, 6 altos, 11 medios y 11 bajos), uno por commit, sin funcionalidades nuevas:

- **Frontend (backoffice y web):** pantallas de error de Next.js (`error.tsx`, `global-error.tsx` y `not-found.tsx`) con "Reintentar" y "Volver al inicio". Mensajes legibles para cualquier estado HTTP o respuesta no JSON, y `toUserMessage` para no mostrar nunca un error técnico. Cliente del tracker de talento con timeout, captura de red y listas comprobadas. Guardado parcial distinguido, "Reintentar" en todas las cargas, indicación de qué hacer tras un error del análisis, `finally` en los formularios, fechas no válidas como "—", y `localStorage` bloqueado sin romper la sesión.
- **Intermediario (BFF):** mensaje genérico si falta `API_BASE_URL`, y log `[BFF]` de los 502 y 504 sin cabeceras ni cuerpo.
- **API:** un CSV mal formado da 422 `malformed_csv` en lugar de 500. Los 404 y 405 del framework y los errores de validación de Pydantic están en español. Los fallos de Resend se registran con su estado y tipo, sin el destinatario, y el envío tiene un timeout de 10 s. `uv run seed` y `uv run create-admin` escriben los errores en `stderr` y terminan con su código de salida.
- **Scripts:** `analyze.py` gestiona los errores de lectura, de codificación y de escritura de `results.csv`, y la cancelación con Ctrl+C. `seed_incidents.py` gestiona la lectura del CSV y la apertura, corrupción y escritura de la base.
- **Verificación:** 559 pruebas pytest (20 nuevas), 36 del analizador y 20 del seed; `tsc`, `lint` y `build` del backoffice y la web. Cada corrección se probó por separado (simulaciones en Node, servidores reales para el BFF y ejecuciones reales de los scripts).
- **Documentación:** `docs/BRIEFING_DIVERGENCES.md`, sección "Auditoría de gestión de errores", con tres divergencias: el detalle técnico en `/funciones`, la ruta absoluta de la base en los comandos de consola y el ámbito de las capturas de `create-admin`. También los README de la API, del backoffice, de `scripts/` y del analizador, y `techContext.md` (código `malformed_csv`).
- **Pendiente:** la prueba manual en el navegador de los estados de error (opcional), fusionar el PR #12 (tras el #11) y la entrega; lo hace el desarrollador.

**Pull requests (comprobados en GitHub el 2026-11-10).** Forman una cadena: cada PR parte de la rama del anterior.

| PR | Rama → destino | Estado |
|---|---|---|
| #6 Analizador de incidentes | `features/csv-reader` → `main` | ✅ Fusionado |
| #7 Directorio de proveedores | `directorio-prov` → `main` | ✅ Fusionado |
| #8 AUTH-01 | `feature/auth-api` → `main` | ⏳ Abierto; listo para fusionar (destino cambiado a `main` el 2026-11-09) |
| #9 AUTH-02 | `feature/auth-frontend` → `feature/auth-api` | ⏳ Abierto |
| #10 AUTH-03 | `feature/password-reset` → `feature/auth-frontend` | ⏳ Abierto |
| #11 Gestor de incidencias | `feature/incident-manager` → `feature/password-reset` | ⏳ Abierto |
| #12 Auditoría de gestión de errores | `feature/error-handling-audit` → `feature/incident-manager` | ⏳ Abierto |

- **Orden de merge:** #8, #9, #10, #11 y #12, con "Create a merge commit" (sin squash ni rebase), para que los PR siguientes no repitan commits ni den conflictos. Al fusionar cada uno hay que borrar su rama de origen ("Delete branch"): así GitHub cambia a `main` el destino del siguiente PR.
- **Ramas:** `features/csv-reader` ya está borrada (local y GitHub). `directorio-prov` sigue en ambos sitios; ya no la usa ningún PR y puede borrarse cuando el desarrollador decida. El `main` local va por detrás de `origin/main`.

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
| **Autenticación** (`/login`, `/register`, grupo `(protegido)` con `SessionProvider`, `lib/api-client.ts`) | ✅ Implementado en `feature/auth-frontend` (`fb35b8d`), incluido `/account/profile`. AUTH-03 añade `/forgot-password`, `/reset-password` y `/account/change-password` (`feature/password-reset`). El filtro de `lib/tools.ts` por permisos sigue sin implementar |
| **Formación** | ❌ No iniciado; será una herramienta del backoffice, no una aplicación aparte |

**Intermediario (BFF)** (`app/api/[...path]/route.ts`): reenvía `GET`, `POST`, `PUT`, `PATCH` y `DELETE` de `/api/<ruta>` a `API_BASE_URL` (la API de Brasaland) sin lógica, incluida la cabecera `Authorization`. ✅ Implementado; lo usan `/incidencias`, `/proveedores`, el login y el registro.

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
| Dominios `auth`, `users` y `profiles` — login JWT, `GET /auth/me`, CRUD de usuarios, `/profiles/me` y `/profiles/{user_id}`, `get_current_user`, `uv run create-admin`; 135 pruebas pytest (más 35 de `core` y 59 de rutas protegidas) | ✅ Implementados en `feature/auth-api`; TinyDB en `storage/auth-db.json` |
| Resto de dominios (`locations`, `recruitment`…) | ❌ No iniciado |
| Base de datos | ⏳ TinyDB provisional para `suppliers` (directiva del CTO); el motor definitivo (Postgres con ORM) está sin decidir. Usuarios y perfiles se quedan en TinyDB también después (directiva del briefing AUTH-01) |
| Autenticación / Autorización | ✅ JWT stateless (sin sesiones ni cookies). Todas las rutas exigen token salvo login, registro, `/health` y las de restablecimiento de contraseña (AUTH-03). Cambiar o restablecer la contraseña cierra las sesiones anteriores. El backoffice envía el token a través del BFF (`feature/auth-frontend`). ⏳ Permisos por rol solo en la gestión de usuarios (admin) |

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
| `packages/shared/` — `brasaland-shared` (Python: reglas del CSV de incidentes) y `@repo/shared-types` (Id, BaseEntity) | ✅ El paquete Python lo usan la API, el analizador y el seed (`feature/incident-manager`); los tipos TypeScript, aún sin consumidores |
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

0. **Entregar la auditoría de gestión de errores (rama `feature/error-handling-audit`)** — Los 29 hallazgos están corregidos, verificados y documentados (2026-11-09). Commit de cierre `d8f39c2`; PR #12 abierto, contra `feature/incident-manager` mientras el #11 no se fusione. La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Auditoría de gestión de errores").

0. **Entregar el gestor de incidencias (rama `feature/incident-manager`)** — Implementado, verificado, documentado y con commit (`ccd09cc`). PR #11 abierto, contra `feature/password-reset` mientras el #10 no se fusione. La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Gestor de incidencias centralizado").

0. **Entregar AUTH-03 (rama `feature/password-reset`)** — Implementado, verificado y documentado. Commits `e87121c` y `2906225`; PR #10 abierto, contra `feature/auth-frontend` mientras el #9 no se fusione. La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Recuperación y cambio de contraseña", con la verificación de los 12 criterios).

0. **Entregar AUTH-02 (rama `feature/auth-frontend`)** — Implementado, verificado, documentado y con commit (`fb35b8d`). PR #9 abierto, contra `feature/auth-api` mientras el #8 no se fusione. La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Autenticación en el frontend").

0. **Entregar AUTH-01 (rama `feature/auth-api`)** — Implementado, verificado y documentado. PR #8 abierto contra `main` y listo para fusionar; es el primero de la cadena. La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Autenticación y protección de rutas").

0. ✅ **Directorio de proveedores (milestone 09)** — PR #7 aprobado y fusionado en `main` (2026-11-08). Sus justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Directorio de proveedores").

0. ✅ **Fase 2 del procesador de incidentes** — PR #6 aprobado y fusionado en `main` (2026-11-08). Sus justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Procesador de reportes de incidentes").

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

- **Backend incipiente**: solo existen los dominios `incidents` (su último análisis vive en memoria), `suppliers` (TinyDB provisional) y la autenticación JWT. El tracker sigue usando la API de playground.
- **Sin base de datos definitiva**: TinyDB es provisional y solo para `suppliers`. Falta decidir el motor (el CTO apunta a Postgres con ORM), las migraciones y el esquema. TinyDB no está pensado para muchos procesos escribiendo a la vez.
- **`suppliers` frente a `procurement`**: la propuesta reservaba los proveedores para `procurement/`. Cuando se aborden el historial de precios y las compras, hay que integrar ambos dominios para que solo uno sea dueño de los proveedores (propuesta, 2.7).
- **Dependencia de Python para agentes**: el esqueleto está en Python, pero el resto del stack es TypeScript/JavaScript — se debe decidir si los agentes serán Python puro o se integran vía MCP/subprocess.
- **Sin gestor de monorepo**: no hay `package.json` raíz ni scripts compartidos; cada proyecto se gestiona independientemente.
- **Website no publicable aún**: el envío del formulario es simulado, faltan los términos del programa y las sedes usan datos de ejemplo. El detalle está en `uis/website/README.es.md`.
- **Sesión del backoffice con límites conocidos** (AUTH-02):
  - el token vive en `localStorage`, como exige el ticket, así que un script inyectado podría leerlo (la propuesta 5.2 preveía una cookie `httpOnly`);
  - el registro es abierto, así que cualquiera puede crearse una cuenta `user`, y no hay permisos por herramienta;
  - la comprobación de sesión es del navegador; la protección de los datos está en la API.
- **Dependencia temporal del backoffice**: mientras exista `packages/brasa-core`, se construye desde la raíz del repositorio, y los cambios en el paquete también deben comprobar `uis/backoffice`.

---

_Actualizado: 2026-11-10_