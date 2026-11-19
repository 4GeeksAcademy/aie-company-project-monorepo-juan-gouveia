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
- **PR:** #8, fusionado en `main` el 2026-11-18.

**Autenticación en el frontend (ticket AUTH-02) completada en la rama `feature/auth-frontend`**, creada desde `feature/auth-api` porque su PR sigue abierto. Las 6 fases (0 a 5) están hechas y revisadas por el desarrollador (2026-11-06):

- **Alcance:** solo `uis/backoffice`; el website público (Hito 1) no cambia. Las decisiones F-1 a F-8 están en `docs/_private/plan-auth-frontend.md`.
- **Token y llamadas:** el token se guarda en `localStorage`. `lib/api-client.ts` lo envía en `Authorization: Bearer` al BFF, que ahora reenvía esa cabecera y también `PUT`. Ante un 401 o un 403 `inactive_user`, borra el token y redirige a `/login?next=&reason=`. `proveedores` e `incidencias` lo usan, y vuelven a funcionar con sesión.
- **Vistas:** `/login` y `/register` (`POST /users` y después login, errores por campo, botón para mostrar la contraseña) en el grupo `app/(publico)/`. `/account/profile` (protegida) muestra el email y el perfil de `GET /auth/me` y edita nombre, teléfono y dirección con `PUT /profiles/me`.
- **Protección:** las demás vistas están en `app/(protegido)/`, cuyo layout es un guard en el cliente (`SessionProvider`). Sin token redirige; con token valida con `GET /auth/me` antes de mostrar nada, y sincroniza la sesión entre pestañas. La cabecera tiene "Mi perfil" y "Cerrar sesión".
- **Verificación:** `tsc`, `lint` y `build` pasan; 361 pruebas de la API pasan; el website no cambia. Los flujos del BFF se probaron en vivo con bases temporales, y los del navegador los revisó el desarrollador.
- **Documentación:** `docs/BRIEFING_DIVERGENCES.md` (sección "Autenticación en el frontend", con la tabla de verificación), `docs/ARCHITECTURE_PROPOSAL.md` (5.2: token en `localStorage` reenviado por el BFF) y los README.
- **Commit:** `fb35b8d`, hecho por el desarrollador.
- **PR:** #9, fusionado en `main` el 2026-11-18.

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
- **PR:** #10, fusionado en `main` el 2026-11-18.

**Gestor de incidencias centralizado completado en la rama `feature/incident-manager`**, creada desde `feature/password-reset` (`2906225`) porque los PR de AUTH siguen abiertos. Commit `ccd09cc`; PR #11 fusionado en `main` (2026-11-18). Decisiones G-1 a G-13 aprobadas y las 5 fases hechas (2026-11-08); el formulario y el panel, revisados por el desarrollador en el navegador:

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

**Auditoría de gestión de errores completada en la rama `feature/error-handling-audit`**, creada desde `feature/incident-manager` (2026-11-09). Commit de cierre `d8f39c2`; PR #12 fusionado en `main` (2026-11-18). Se auditó todo el repositorio y se corrigieron los 29 hallazgos (1 crítico, 6 altos, 11 medios y 11 bajos), uno por commit, sin funcionalidades nuevas:

- **Frontend (backoffice y web):** pantallas de error de Next.js (`error.tsx`, `global-error.tsx` y `not-found.tsx`) con "Reintentar" y "Volver al inicio". Mensajes legibles para cualquier estado HTTP o respuesta no JSON, y `toUserMessage` para no mostrar nunca un error técnico. Cliente del tracker de talento con timeout, captura de red y listas comprobadas. Guardado parcial distinguido, "Reintentar" en todas las cargas, indicación de qué hacer tras un error del análisis, `finally` en los formularios, fechas no válidas como "—", y `localStorage` bloqueado sin romper la sesión.
- **Intermediario (BFF):** mensaje genérico si falta `API_BASE_URL`, y log `[BFF]` de los 502 y 504 sin cabeceras ni cuerpo.
- **API:** un CSV mal formado da 422 `malformed_csv` en lugar de 500. Los 404 y 405 del framework y los errores de validación de Pydantic están en español. Los fallos de Resend se registran con su estado y tipo, sin el destinatario, y el envío tiene un timeout de 10 s. `uv run seed` y `uv run create-admin` escriben los errores en `stderr` y terminan con su código de salida.
- **Scripts:** `analyze.py` gestiona los errores de lectura, de codificación y de escritura de `results.csv`, y la cancelación con Ctrl+C. `seed_incidents.py` gestiona la lectura del CSV y la apertura, corrupción y escritura de la base.
- **Verificación:** 559 pruebas pytest (20 nuevas), 36 del analizador y 20 del seed; `tsc`, `lint` y `build` del backoffice y la web. Cada corrección se probó por separado (simulaciones en Node, servidores reales para el BFF y ejecuciones reales de los scripts).
- **Documentación:** `docs/BRIEFING_DIVERGENCES.md`, sección "Auditoría de gestión de errores", con tres divergencias: el detalle técnico en `/funciones`, la ruta absoluta de la base en los comandos de consola y el ámbito de las capturas de `create-admin`. También los README de la API, del backoffice, de `scripts/` y del analizador, y `techContext.md` (código `malformed_csv`).
- **Pendiente:** la prueba manual en el navegador de los estados de error (opcional), fusionar el PR #12 (tras el #11) y la entrega; lo hace el desarrollador.

**Pruebas de la API de autenticación (ticket AUTH-088) completadas en la rama `feature/auth-tests`**, creada desde `feature/error-handling-audit` (`d8f39c2`) el 2026-11-10; local, sin subir. Decisiones T-1 a T-9 aprobadas y fases 0 a 6 del núcleo hechas, con un commit por fase hecho por el desarrollador:

- **API (pytest):** 16 módulos en `tests/auth/` (`test_token.py` y uno por cada uno de los 15 endpoints de `auth`, `users` y `profiles`), 146 casos con camino feliz, caso límite y modo de fallo. Llaman a las funciones de ruta y a los servicios, sin HTTP. Con ellos solos, la cobertura de autenticación es del **88 %** (objetivo: 70 %).
- **Integración HTTP:** las 99 pruebas de router de auth que ya existían (214 casos) pasaron a `tests/integration/`, con el marker `integration`.
- **Backoffice (Jest):** Jest con ts-jest en `uis/backoffice` (`npm test`, `npm run test:coverage`) y 55 pruebas en `__tests__/auth/`: validación de formularios, destino tras el login, token en `localStorage` y reparto de los errores de la API. `lib/auth/` queda al 96 %.
- **Bugs encontrados y corregidos** (los dos salieron de la revisión asistida por IA y tienen prueba de regresión):
  - H-1 (`bcc45b7`): cambiar la contraseña por `PUT /users/{id}` no cerraba las sesiones anteriores;
  - H-2 (`c6fc80d`): `change-password` respondía «contraseña actual incorrecta» si la cuenta se borraba durante el cambio.
- **Cambio de producción para las pruebas:** la decisión del login pasó a `issue_login_token` (`auth/router.py`), sin cambiar el comportamiento.
- **Verificación:** `uv run pytest` 705 pasan; `npm test` 55 pasan; `tsc`, `lint` y `build` del backoffice pasan.
- **Documentación:** `services/brasaland-api/TESTING.md` y `TESTING.es.md` (plan, cómo ejecutar, cómo están construidas, revisión con IA, bugs, Jest y cobertura); README de la API y del backoffice; `docs/BRIEFING_DIVERGENCES.md`, sección "Batería de pruebas de autenticación" (7 divergencias y la tabla de los 8 criterios).
- **Extra API-042 completado:** 11 módulos y 101 casos en `tests/suppliers/` y `tests/incidents/` (los 6 endpoints de proveedores y los 5 del gestor de incidencias, sin HTTP); con ellos solos, la cobertura de los dos dominios es del 84 % (objetivo: 60 %). Las pruebas de router de los dos dominios pasaron a `tests/integration/`. `uv run pytest`: 806 pasan.
- **Extra FE-019 completado:** 35 pruebas de Jest en `uis/backoffice/__tests__/utils/` para `lib/format.ts`, `toUserMessage` y `readJson`, todas al 100 %; `jest.config.js` fija `TZ=UTC`. El backoffice tiene 90 pruebas de Jest.
- **PR:** #13, fusionado en `main` el 2026-11-18.

**Gestión de inventario con ORM (Hito 5, ticket BRD-0512) completada en la rama `feature/inventory-orm`**, creada desde `feature/auth-tests` (`65f2a76`) el 2026-11-14 porque el PR #13 sigue abierto. Decisiones D1 a D7 aprobadas (en `docs/_private/briefing-inventario-backend.md`) y fases 0 a 6 hechas, con un commit por fase hecho por el desarrollador:

- **Dos conexiones:** TinyDB para la autenticación (sin cambios) y Supabase (PostgreSQL) con SQLModel para el inventario. `app/core/database.py` tiene el motor (`DATABASE_URL` en `.env`; la API no arranca sin ella), `create_all` al arrancar y `get_db` (una sesión por petición). Driver psycopg2 fijado en la URL, porque SQLAlchemy 2.1 elige psycopg 3 (corrección `2980037`).
- **Dominio `inventory`:** `Ingredient`, `IngredientEntry` e `IngredientExit` con los nombres del briefing, FK de las órdenes a `ingredients` y sin columna de stock; schemas aparte. 6 rutas bajo `/api/v1/inventory`, todas protegidas, sin rutas de edición. `current_stock` = entradas − salidas, calculado en SQL y global por ingrediente (`?country=CO|US`). Las salidas que dejarían el stock en negativo dan 400 `insufficient_stock` (mensaje en español) antes de escribir. `user_uuid` sale del token. Sin N+1: 1 consulta en `GET /products` y 2 en `GET /orders`.
- **Semilla:** `uv run --env-file .env seed-inventory` (6 ingredientes, 4 entradas y 3 salidas; stock 52/32/20/0), idempotente, con el UUID del administrador activo más antiguo. Cargada en Supabase.
- **Verificación:** `uv run pytest`: 916 pasan (110 nuevas; cobertura del dominio, 97 %). En vivo contra Supabase (2026-11-14): semilla dos veces, stock, filtro por país, 400 sin escritura, 422 con `user_uuid` o `reason` inválido, `GET /orders`, 401 sin token y 405 al intentar editar el stock.
- **Documentación:** `docs/BRIEFING_DIVERGENCES.md`, sección "Gestión de inventario con ORM" (D1–D7, decisiones y la tabla de verificación de los criterios de evaluación); README de la API y de `services/`; `techContext.md`; `ARCHITECTURE_PROPOSAL.md` (quinto bloque en 2.7 y sección 7).
- **PR:** #14, fusionado en `main` el 2026-11-18. La herramienta de inventario del backoffice llegó en la fase frontend (párrafo siguiente).

**Inventario en el backoffice (Hito 5, fase frontend, BRD-0512) completado en la rama `feature/inventory-frontend`**, creada desde `feature/inventory-orm` el 2026-11-14 porque el PR #14 sigue abierto. Decisiones F1 a F6 aprobadas (en `docs/_private/briefing-inventario-backend.md`) y fases 0 a 5 hechas, con un commit por fase hecho por el desarrollador:

- **Integración:** `uis/backoffice/lib/inventory.ts` es el único módulo que llama a `/api/inventory/...`, con `apiJson` (token en `Authorization`, errores legibles, cierre de sesión ante un 401). Va por el intermediario con `API_BASE_URL`, sin `NEXT_PUBLIC_INVENTORY_API_URL` (F1).
- **Vistas** (rutas en español, F2): `/inventario/ingredientes` (stock con nivel por unidad, F4), `/inventario/ordenes/entrada`, `/inventario/ordenes/salida` (stock reactivo, aviso que no bloquea y 400 junto a la cantidad) y `/inventario/ordenes` (historial con "Tú", F6). Herramienta "Inventario" en `lib/tools.ts`. La columna `user_uuid` se rotula "Usuario" (cambio del 2026-11-16).
- **Verificación:** `npm test` 159 pasan (69 de inventario); `tsc`, `lint` y `build` pasan. En vivo contra una API temporal (SQLite y TinyDB fuera del repositorio), sin tocar Supabase.
- **Documentación:** `docs/BRIEFING_DIVERGENCES.md`, sección "Inventario en el backoffice" (divergencias, decisiones y tabla de los 10 criterios); README del backoffice.
- **Ajustes tras el plan (commit aparte):** pestañas del inventario en dos líneas en móvil, y Proveedor de la entrada como lista de los proveedores activos del directorio, filtrada por el país y la categoría equivalente del ingrediente (`lib/inventory-suppliers.ts`).
- **PR:** #15, fusionado en `main` el 2026-11-18. Los cambios de cabecera y menú (iconos de la cuenta, menú agrupado y hamburguesa en móvil y tablet) van en la rama `feature/backoffice-navigation`, creada desde esta.

**Navegación del backoffice completada en la rama `feature/backoffice-navigation`**, creada desde `feature/inventory-frontend` (`3c7fe3d`) el 2026-11-16 porque el PR #15 sigue abierto. Sin ticket; un commit por cambio:

- **Cuenta:** "Mi perfil" y "Cerrar sesión" solo con iconos en todos los tamaños, con un tooltip propio (`components/Tooltip.tsx`) al pasar el ratón o llegar con el teclado.
- **Menú por secciones:** `lib/tools.ts` agrupa las herramientas en `toolSections` (Inventario, Proveedores, Incidencias y Herramientas). En la cabecera, las secciones con varias herramientas son desplegables (`components/NavDropdown.tsx`), y la portada muestra las mismas secciones.
- **Menú hamburguesa** por debajo de `xl` (`components/MobileNav.tsx`): panel superpuesto bajo la cabecera, sin cambiar su altura. Ya se puede navegar desde cualquier página en móvil y tablet, así que la divergencia del menú del gestor de incidencias queda resuelta (`docs/BRIEFING_DIVERGENCES.md`).
- **PR:** #16, fusionado en `main` el 2026-11-18.

**Contenedorización del monorepo (ticket #infra-40) completada en la rama `feature/dockerize`**, creada desde `feature/backoffice-navigation` (`64f0d68`) el 2026-11-16 porque el PR #16 sigue abierto. El objetivo es que `docker compose up` desde la raíz levante dos servicios en la red `brasaland-net`: `uis` (website en el 3000 y backoffice en el 3001, con `next dev`) y `api` (Uvicorn con `--reload`). Ambos usan bind mounts y leen sus variables del `.env` de la raíz. El despliegue al VPS de la consigna quedó fuera de alcance: ese apartado se eliminó. Los paquetes `packages/shared` y `packages/brasa-core` entran a las imágenes con `additional_contexts` de Compose.

- **Fase 0 (`20c10ce`):** `.env.example` en la raíz (con `API_BASE_URL=http://api:8000/api/v1`), `services/requirements.txt` generado desde `uv.lock` y `.gitattributes` (`*.sh` con LF). El `.env` de la raíz existe en local y no se versiona.
- **Fase 1 (`9cdd4f5`):** `services/Dockerfile` (`python:3.12-slim`, `uv` 0.13.7 copiado de la imagen oficial de Astral, `uv pip install -r requirements.txt`, `packages/shared` editable desde el contexto adicional `shared`, Uvicorn con `--reload` y usuario sin privilegios) y `services/.dockerignore`. La imagen se construye y `app.main` se importa dentro del contenedor.
- **Fase 2 (`f84b9c1`):** `uis/Dockerfile` (`node:22-alpine`, usuario `node`, `npm ci` por aplicación y `packages/brasa-core` desde el contexto adicional `brasa-core`), `uis/.dockerignore` y `uis/start.sh` (las dos apps con `next dev`, salida con prefijo, reenvío de señales y salida con error si una se cae). Como Turbopack no lee `WATCHPACK_POLLING` y Docker Desktop no propaga los eventos de archivos de Windows, los dos `next.config.ts` activan `watchOptions.pollIntervalMs` solo si existe `NEXT_WATCH_POLL_INTERVAL_MS` (la define Compose; fuera de Docker no cambia nada).
- **Fase 3 (`80944a8`):** `docker-compose.yml` en la raíz (proyecto `brasaland`): servicios `api` (8000, healthcheck contra `/health`) y `uis` (3000 y 3001, arranca cuando `api` está healthy), red `brasaland-net`, bind mounts del código y de `packages/`, y volúmenes anónimos para `.venv`, `node_modules` y `.next`. Cada servicio recibe solo sus variables, interpoladas desde el `.env`; si faltan `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` o `DATABASE_URL`, Compose se detiene con un mensaje claro. Comprobado: `docker compose up -d --build` levanta los dos servicios, responden desde el host y `uis` llega a `api` por su nombre (también a través del BFF).
- **Fase 4 (`ba3eae3` y `e780588`, verificación):** arranque desde cero (`down -v`, `build --no-cache`, `up -d`) sin pasos manuales; las páginas responden desde el host; `uis` y `api` se alcanzan por nombre en los dos sentidos; el BFF llega a la API (401 sin token, y login real con una cuenta temporal que después se borró, con lectura del inventario en Supabase); la recarga en caliente funciona en la API y en las dos apps con cambios hechos desde Windows; ningún secreto real en archivos versionados y el `.env` nunca se ha versionado; en el host pasan `uv run pytest` (916) y `npm test` (163). **Cambio:** Turbopack no detecta cambios en los bind mounts (ni con sondeo), así que en Docker las dos apps arrancan con `next dev --webpack` (`uis/start.sh`); fuera de Docker sigue Turbopack.
- **Fase 5 (documentación):** sección "Ejecutar con Docker" en el README raíz (`.md` y `.es.md`: requisitos, `cp .env.example .env`, servicios y URL, recarga, datos y comandos útiles), notas en los README de `uis/` y `services/`, `techContext.md` y la sección "Contenedorización del monorepo" de `docs/BRIEFING_DIVERGENCES.md` (VPS fuera de alcance, contextos adicionales, `requirements.txt` desde `uv.lock`, webpack en Docker, sondeo, el `.env` como paso previo, el PR contra la rama anterior, decisiones y la tabla de los 8 criterios).
- **Commit de la Fase 5:** `b1cab16`.
- **PR:** #17, abierto el 2026-11-17; desde el 2026-11-18 apunta a `main` (7 commits), con la captura de `docker compose ps`.

**Auditoría de rendimiento de ambos frontends completada en la rama `feature/performance-audit`**, creada desde `feature/dockerize` (`b1cab16`) el 2026-11-17 porque el PR #17 sigue abierto. Ciclo medir → analizar → corregir → volver a medir con Lighthouse 13.5.0 (la de DevTools en Chrome 157) sobre el build de producción (`build` + `start`) servido en local, fuera de Docker. Las cifras son la mediana de 3 ejecuciones del CLI; las capturas, de DevTools. Todo está en `audit/`.

- **Medición inicial (`a499311`):** `audit/before/` (6 capturas y JSON). Páginas: website `/` y `/registro` en escritorio y móvil; backoffice `/` y `/gestor-incidencias` en escritorio, con sesión.
- **Análisis (`64e2728`):** `audit/AUDIT.md` (5 problemas con su causa raíz y 3 refactorizaciones), guiado por las skills `core-web-vitals` y `performance` de `addyosmani/web-quality-skills`, instaladas en `.claude/skills/` sin commit.
- **Correcciones:**
  - P1 `48b27eb`: el resumen del gestor reserva su espacio mientras carga; CLS de hasta 0,204 → 0, y Performance 100;
  - P3 `5c2f412`: icono del website (`app/icon.tsx`); Best Practices 96 → 100 en las 4 mediciones;
  - P2 (fachada sin `loading="eager"`) se midió y se revirtió: no mejoraba el LCP en móvil y empeoraba el escritorio.
- **Refactorizaciones:**
  - R1 `8ed12c2`: hook `useAsyncData` en 5 hooks del backoffice, con 7 pruebas nuevas (Jest 170/170);
  - R2 `448ee2b`: componente `RetryableError` en 8 archivos;
  - R3 `ae6eb10`: componente `BrandLogo` en las dos cabeceras del website.
- **Medición final (`6f7f0c3`):** `audit/after/`.
- **Informe:** `audit/REPORT.md` (comparativa, valoración y criterios). Divergencias en `docs/BRIEFING_DIVERGENCES.md` (sección "Auditoría de rendimiento de ambos frontends").
- **PR:** #18, abierto el 2026-11-17 contra `feature/dockerize` mientras el #17 no se fusione.

**Auditoría de serialización del backend completada en la rama `feature/serialization-audit`**, creada desde `feature/performance-audit` (`cd078c9`) el 2026-11-18 porque los PR #17 y #18 siguen abiertos. El objetivo es que cada endpoint de `services/brasaland-api` tenga un `response_model` explícito y ajustado a lo que usa su consumidor, sin campos sensibles ni email en las rutas de auth no autenticadas. Decisiones D1 a D5 aprobadas (en `docs/_private/plan-auditoria-serializacion.md`); un commit por fase y subfase, hechos por el desarrollador.

- **Auditoría (Fase 1):** `docs/serialization-audit.md`. Hay 35 endpoints: 23 ✅, 10 ⚠️, 1 ❌ (`GET /health`) y 1 excepción documentada (la exportación CSV). Ningún endpoint devuelve un ORM en crudo ni contraseñas. El trabajo pendiente está en el registro (reenvía el email), en los perfiles (exponen `id` y `user_id`), en el listado de incidencias (usa el esquema de detalle) y en las órdenes del inventario (ingrediente anidado junto a su clave foránea).
- **Implementación (Fase 2), con el backoffice adaptado en el mismo commit:**
  - 2a `d618a8a`: el registro devuelve `{id, message}`, y los perfiles y `/auth/me` usan `ProfileRead` (sin `id` ni `user_id`);
  - 2b `857802f`: las órdenes del inventario llevan el ingrediente aplanado (`ingredient_name`, `ingredient_sku`, `ingredient_unit`);
  - 2c `ad55908`: el listado de incidencias usa `IncidentListItem` (sin `updated_at`), `/health` usa `HealthResponse` y la exportación CSV declara `response_model=None` como excepción documentada;
  - 2d `1c19ca5`: la guarda `tests/integration/test_response_models.py` exige, sobre OpenAPI, modelos con nombre, ninguna contraseña ni token en las respuestas, ningún email en los flujos de auth salvo `/auth/me` y entradas separadas de las salidas.
- **Verificación (Fase 3):**
  - `uv run pytest`: 926 pasan (916 + 10);
  - backoffice: Jest 170, `tsc`, lint y build sin errores;
  - el OpenAPI solo cambia en lo previsto;
  - prueba manual en `/docs` de 5 endpoints, con una cuenta temporal que después se borró.
  Los 35 endpoints quedan ✅. La excepción del CSV está en `docs/BRIEFING_DIVERGENCES.md` (sección 13).
- **PR:** #19, abierto el 2026-11-18 contra `feature/performance-audit` mientras el #18 no se fusione (6 commits, head `9f0da00`).

**Estrategia de caching completada en la rama `feature/caching-optimisation`**, creada desde `feature/serialization-audit` (`9f0da00`) el 2026-11-18 porque los PR #17, #18 y #19 siguen abiertos. Un commit por fase, hechos por el desarrollador. Informe: `docs/CACHING_REPORT.md`.

- **Medición (Fases 1 y 2):** middleware de timing `app/core/timing.py` (logger `api.timing`) y seeder `scripts/seed_volume.py` (150 ingredientes y ~21 000 órdenes en Supabase, 10 000 incidencias en TinyDB, marca `VOL-`). Con volumen, `GET /inventory/orders` tarda 1,3 s y `/inventory/products` ~100 ms (ida y vuelta a Supabase); las lecturas de TinyDB, 30–230 ms por releer el archivo entero.
- **Backend (Fase 3):** `core/cache.py` (`TTLCache`, con contador de generación) y `inventory/cache.py`: `GET /products` 60 s y `GET /orders` 5 min, JSON ya serializado y `X-Cache`. Las tres escrituras del inventario invalidan tras el `commit`. Un acierto tarda 1,4 ms. No se cachean la sesión, los perfiles, `products/{id}` ni TinyDB (la solución es migrar).
- **Frontend (Fase 4):** `next/dynamic` para `SupplierFormModal` y `CandidateFormModal`; historial y gestor pintados de 50 en 50 (`useShowMore`): el historial pasa de 4,7 s a 0,17 s, y un cambio de estado en el gestor, de 740 ms a 11 ms. El filtro del historial usa `useMemo` (~30 ms en móvil).
- **Verificación:** API 952 pruebas, Jest 180, `tsc`, lint y build sin errores, y prueba funcional en Chrome. Las divergencias están en `docs/BRIEFING_DIVERGENCES.md` (sección 14).
- **PR:** #20, abierto el 2026-11-18 contra `feature/serialization-audit` mientras el #19 no se fusione (5 commits, head `95538a6`).
- **Datos de volumen:** siguen cargados (`VOL-`) en Supabase y en `brasaland-db.json` local, con 4 incidencias en `in_progress` por la medición; se retiran con `scripts/seed_volume.py --clear`.

**Plan de Telemetría completado en la rama `feature/telemetry-plan`**, creada desde `feature/caching-optimisation` (`95538a6`) el 2026-11-18 porque los PR #17 a #20 siguen abiertos. Responde al RFI del equipo de gestión sin escribir código. Un commit por fase.

- **Catálogo (Fase 1):** 44 eventos, entre ellos las 6 métricas obligatorias del briefing con su disparo exacto en la API y 38 oportunidades en 7 categorías (inventario, autenticación, navegación, rendimiento, errores, otras áreas del negocio y procesos internos). Cada evento tiene la frase de la regla de oro y su responsable. El flujo de inventario tiene 9 puntos de instrumentación.
- **Diseño (Fase 2):** envelope con los nombres literales del enunciado, más `source` y `environment`; datos sensibles (seudónimos, HMAC del email, IP truncada); una ficha y un allowlist por evento. `docs/telemetry/event-schemas.json` es JSON Schema draft-07 validado (44 ejemplos y 220 casos negativos).
- **Entrega (Fase 3):** 12 eventos en stream y 32 en batch, según la urgencia de la decisión; throttle en 15; riesgos y exclusiones; y 11 brechas con el modelo actual, que son la primera tarea de la fase de captura.
- **PR:** #21, abierto el 2026-11-18 contra `feature/caching-optimisation` mientras el #20 no se fusione (3 commits, head `95b8b6e`).

**Captura de eventos de telemetría completada en la rama `feature/telemetry-capture`**, creada desde `feature/telemetry-plan` (`95b8b6e`) el 2026-11-19 porque los PR #17 a #21 siguen abiertos. El backoffice captura los eventos con una única función `track()` y los envía en lotes a un receptor provisional de la API (`POST /telemetry/events`), que valida el formato y responde 200 sin guardar nada. Decisiones C1 a C9 aprobadas (en `docs/_private/plan-captura-telemetria.md`); un commit por fase.

- **Fase 0 (plan y esquemas):** sección 13 del plan ("Fase de captura en el backoffice") y fichas en la 14. Alcance de 34 eventos: los 6 obligatorios, el piso técnico (vistas, errores de JavaScript y Web Vitals), autenticación, inventario, errores y latencia de la API, navegación, proveedores e incidencias. Los otros 10 esperan al emisor de la API. 26 eventos pasan a `source: "browser"`, `login_failed` 2.0.0 (sin huella ni red, con `network_error`), `api_connection_failed` 1.1.0 (`api_timeout`), `sessionId` desde el login y lotes de 20 eventos o 10 s. `event-schemas.json` (catálogo 1.1.0) validado sin fallos.
- **Fase 1 (receptor en la API):** dominio `telemetry` con `POST /telemetry/events`, fuera de `/api/v1` y público. Valida el lote (de 1 a 100 eventos) con `TelemetryEvent`, el envelope del plan (10 campos, sin extras), acepta `application/json` y `text/plain` (`sendBeacon`), registra la cantidad y el `event_type` de cada evento en `api.telemetry` y responde `{"received": N}` sin guardar nada (413 con más de 256 KB). Tiene CORS solo para el origen de `FRONTEND_URL` y solo en `/telemetry`. `TELEMETRY_ENDPOINT` es opcional en la configuración. El middleware de timing lee o crea `X-Request-Id`, lo devuelve y lo escribe al final de su línea. La ruta se auditó como la operación 36 (`docs/serialization-audit.md`, sección 11). `uv run pytest`: 1022 pasan (70 nuevas); probado en vivo con una API temporal (JSON, `text/plain`, CORS, 422 y log).
- **Fase 2 (servicio en el backoffice):** `lib/telemetry/` exporta solo `track(eventType, properties)`. Valida contra `catalog.ts`, generado desde `event-schemas.json` (`npm run telemetry:catalog`; 34 eventos `source: browser`), y descarta lo que no cumple. Añade el envelope: `eventId` y `timestamp` de la captura, `sessionId` (creado al iniciar sesión y guardado en `sessionStorage`), `userId` (el `sub` del token), `schemaVersion` del catálogo, `requestId` (con `withRequestId`), `source` y `environment`. La cola manda lotes de 20 eventos o cada 10 s, reintenta 3 veces (1, 2 y 4 s), guarda como máximo 500 eventos y usa `sendBeacon` en `text/plain` en `visibilitychange` y `pagehide`. `apiFetch` envía `X-Request-Id` y lo guarda en `ApiError`; el BFF lo reenvía (y `X-Cache`). Variables `NEXT_PUBLIC_TELEMETRY_ENDPOINT` y `NEXT_PUBLIC_TELEMETRY_ENVIRONMENT`. Jest: 230 pasan (50 nuevas; cobertura del servicio, 94 %); `tsc`, lint y build pasan. En vivo, el BFF lleva el id a la API y lo devuelve. Todavía no se instrumenta ningún evento.
- **Fase 3a (brechas B5 y B6 y "Ajustar stock"):** `IngredientEntry.unit_cost` (obligatorio y mayor que 0, en la moneda del país) e `IngredientExit.waste_reason` (`expired`, `kitchen_error` o `theft_suspected`; obligatorio en las mermas y prohibido en los consumos, con el 422 en el campo). Las dos columnas admiten NULL para las filas anteriores, y las respuestas las devuelven. La semilla lleva costes y el motivo de su merma. **En Supabase falta ejecutar** `services/brasaland-api/migrations/001_inventory_unit_cost_waste_reason.sql` (lo hace el desarrollador): `create_all` no añade columnas. En el backoffice, el coste unitario en la entrada (con moneda y unidad), el motivo de la merma en la salida, los dos datos en el historial y la acción "Ajustar stock" en `/inventario/ingredientes`, que envía el `PATCH` real (la API responde 405) y explica cómo cambiar el stock con órdenes. API: 1032 pruebas (10 nuevas); Jest: 236 (6 nuevas); `tsc`, lint y build pasan. En vivo a través del BFF con una API temporal: los 201, los dos 422 y el 405.
- **Fase 3b (las 6 métricas obligatorias):** se emiten en la capa de datos al recibir la respuesta de la API, con el `requestId` de su llamada. `lib/inventory.ts` emite `inbound_order_created`, `ingredient_price_variance_detected` (media de 90 días del mismo producto y proveedor, con al menos 3 entradas y un umbral del 10 %, calculada con `GET /inventory/orders`), `outbound_order_created` o `stock_waste_registered` (con `stock_after` pedido a la API) y `stock_threshold_triggered` (al cruzar `LOW_STOCK_THRESHOLDS`). `lib/telemetry/api-events.ts` emite `direct_stock_edit_rejected` desde `apiFetch` (405 en el inventario o 422 por `current_stock`). `supplier_id` sale del directorio; `user_role`, de la sesión validada (`rememberUserRole`). Jest: 264 (28 nuevas); `tsc`, lint y build pasan; las propiedades de los 6 eventos cumplen `event-schemas.json`.
- **Fase 3c (piso técnico, Web Vitals y autenticación):** `TelemetryRoot` en el layout raíz emite `page_viewed` (plantilla de ruta, `initial` o `client`, 1 s de throttle), `frontend_error_captured` (`window.onerror`, `unhandledrejection` y las tres pantallas de error con `useReportBoundaryError`; mensaje saneado, huella FNV-1a de 64 bits, una vez por huella cada 60 s y 20 por página) y `page_performance_recorded` (LCP, CLS e INP de `useReportWebVitals`, un evento por carga al ocultar la pestaña). El listener de ocultación pasa a `window` (`lib/telemetry/lifecycle.ts`), después de Web Vitals y antes del `sendBeacon`. Autenticación: `login_failed`, `login_succeeded` (al validar la sesión), `logout_completed`, `user_registered`, `password_reset_completed`, `password_changed`, `session_expired`, `auth_token_rejected` y `password_reset_link_rejected`. Jest: 300 (36 nuevas); `tsc`, lint y build pasan; las propiedades de los 12 eventos cumplen el esquema.
- **Fase 3d (resto del catálogo, los 34 eventos instrumentados):** errores y rendimiento desde `apiFetch`: `api_latency_recorded` (las lentas y las de error, y 1 de cada 10 del resto por `requestId`, con `X-Cache`), `api_error_returned` (10 s por ruta, código y usuario), `api_connection_failed` (30 s) y `order_validation_failed` (campos e identificadores del cuerpo). `outbound_order_rejected` sale de `createExit`, con el stock del momento. Navegación: `useFormTelemetry` en 6 formularios (`form_validation_failed` cada 2 s y `form_abandoned` al salir, cerrar el modal o la pestaña), `useListFilterTelemetry` en el historial, el gestor y el directorio (debounce de 500 ms y espera al resultado) y `useShowMore` (`list_page_extended`). Negocio: 3 eventos de proveedores y 4 de incidencias desde sus clientes; `IncidentListItem` vuelve a llevar `updated_at` (`docs/serialization-audit.md`, sección 11). Jest: 332 (32 nuevas); API: 1032; `tsc`, lint y build pasan; las propiedades de los 16 eventos de la fase cumplen el esquema.
- **Fase 4 (verificación y documentación):** verificado en DevTools con la API y `next dev` en local: lotes `POST /telemetry/events` con el envelope completo y 200, `inbound_order_created` en el Payload y el envío con `sendBeacon` al redirigir al login tras un 401 (`auth_token_rejected` y, con el token caducado, `session_expired`). Documentación: `docs/BRIEFING_DIVERGENCES.md`, sección 16 (13 divergencias y criterios); plan, sección 13.6 (dónde se captura cada evento); `techContext.md`. La descripción del PR está en `docs/_private/commits-captura-telemetria.md`.
- **Commits:** `96d092e`, `933145b`, `2ecc65a`, `a8e6444`, `6fcea5e`, `1e64501`, `361e64f` y `84772fe`, hechos por el desarrollador.
- **PR:** #22, abierto el 2026-11-19 contra `feature/telemetry-plan` mientras el #21 no se fusione (8 commits, head `84772fe`).

**Almacenamiento de eventos de telemetría en curso en la rama `feature/telemetry-storage`**, creada desde `feature/telemetry-capture` (`84772fe`) el 2026-11-19 porque los PR #17 a #22 siguen abiertos. El receptor `POST /telemetry/events` deja de ser provisional: valida cada evento por separado y guarda los válidos en la tabla `telemetry_events` de Supabase con una sola sentencia por lote; el backoffice no cambia. Decisiones S1 a S11 aprobadas (en `docs/_private/plan-almacenamiento-telemetria.md`); un commit por fase.

- **Fase 0 (plan y esquemas):** sección 14 nueva del plan ("Fase de almacenamiento": la tabla de ocho columnas con sus tres índices, la inmutabilidad con trigger y RLS, el mapeo de evento a fila y el receptor con validación por evento) y fichas en la 15, con el `level`, el `value` y la plantilla del `message` de cada evento. R2 y R4 ajustados a la tabla inmutable. `event-schemas.json` (catálogo 1.2.0) añade `x-level`, `x-value` y `x-message` a los 44 eventos, validado sin fallos; el catálogo del backoffice se regenera idéntico.
- **Fase 1 (tabla):** `services/brasaland-api/migrations/002_telemetry_events.sql` crea `telemetry_events` (ocho columnas, `level` limitado a `info`/`warn`/`error`, `tags` JSONB), sus tres índices (`timestamp`, `event_type` y GIN en `tags`), un trigger que rechaza `UPDATE`, `DELETE` y `TRUNCATE`, y RLS sin políticas con los permisos de `anon` y `authenticated` retirados. Es idempotente; probada en PostgreSQL 17 (PGlite) con los roles de Supabase. **En Supabase falta ejecutarla** (lo hace el desarrollador). Modelo `TelemetryEventRow` con un registro propio: `init_db` no crea la tabla. API: 1037 pruebas (5 nuevas).
- **Fase 2 (receptor real):** `POST /telemetry/events` lee el lote de forma laxa (`TelemetryBatch.events: list[Any]`), valida cada evento con `TelemetryEvent.model_validate` (sin cambios) y con el catálogo generado desde `event-schemas.json` (`catalog.py`, `uv run telemetry-catalog`: tipo, obligatorias, allowlist y valores que PostgreSQL no admite), guarda los válidos con un solo `INSERT … ON CONFLICT (id) DO NOTHING` y responde `{"received", "stored", "rejected"}` (los repetidos cuentan en `stored`). 422 sin lista `events` o con más de 100 (`too_many_events`), 413 por encima de 256 KB y 503 `telemetry_storage_unavailable` si la base falla o falta la tabla (el log pide la migración). Log por lote sin valores. API: 1078 pruebas (41 nuevas): lote mixto, repetidos, una sola sentencia por lote, los 44 ejemplos del esquema, catálogo al día y log sin datos.

**Pull requests (comprobados en GitHub el 2026-11-18).** Forman una cadena: cada PR parte de la rama del anterior.

| PR | Rama → destino | Estado |
|---|---|---|
| #6 Analizador de incidentes | `features/csv-reader` → `main` | ✅ Fusionado |
| #7 Directorio de proveedores | `directorio-prov` → `main` | ✅ Fusionado |
| #8 AUTH-01 | `feature/auth-api` → `main` | ✅ Fusionado (2026-11-18) |
| #9 AUTH-02 | `feature/auth-frontend` → `main` | ✅ Fusionado (2026-11-18) |
| #10 AUTH-03 | `feature/password-reset` → `main` | ✅ Fusionado (2026-11-18) |
| #11 Gestor de incidencias | `feature/incident-manager` → `main` | ✅ Fusionado (2026-11-18) |
| #12 Auditoría de gestión de errores | `feature/error-handling-audit` → `main` | ✅ Fusionado (2026-11-18) |
| #13 AUTH-088 (pruebas, API-042 y FE-019) | `feature/auth-tests` → `main` | ✅ Fusionado (2026-11-18) |
| #14 Hito 5: inventario con SQLModel y Supabase | `feature/inventory-orm` → `main` | ✅ Fusionado (2026-11-18) |
| #15 Hito 5, fase frontend: inventario en el backoffice | `feature/inventory-frontend` → `main` | ✅ Fusionado (2026-11-18) |
| #16 Navegación del backoffice | `feature/backoffice-navigation` → `main` | ✅ Fusionado (2026-11-18) |
| #17 Contenedorización del monorepo (#infra-40) | `feature/dockerize` → `main` | ⏳ Abierto (2026-11-17) |
| #18 Auditoría de rendimiento de ambos frontends | `feature/performance-audit` → `feature/dockerize` | ⏳ Abierto (2026-11-17) |
| #19 Auditoría de serialización del backend | `feature/serialization-audit` → `feature/performance-audit` | ⏳ Abierto (2026-11-18) |
| #20 Estrategia de caching de la API y el backoffice | `feature/caching-optimisation` → `feature/serialization-audit` | ⏳ Abierto (2026-11-18) |
| #21 Plan de Telemetría | `feature/telemetry-plan` → `feature/caching-optimisation` | ⏳ Abierto (2026-11-18) |
| #22 Captura de eventos de telemetría | `feature/telemetry-capture` → `feature/telemetry-plan` | ⏳ Abierto (2026-11-19) |

- **Orden de merge:** del #6 al #16 ya están fusionados (el #8 a #16, el 2026-11-18). Quedan el #17, el #18, el #19, el #20, el #21 y el #22, en ese orden, con "Create a merge commit" (sin squash ni rebase), para que el PR siguiente no repita commits ni dé conflictos. Al fusionar cada uno hay que borrar su rama de origen ("Delete branch"): así GitHub cambia a `main` el destino del siguiente PR.
- **Ramas (2026-11-18):** las ramas fusionadas, incluida `directorio-prov`, están borradas en local y en GitHub. Quedan `main` (al día con `origin/main`), `feature/dockerize`, `feature/performance-audit`, `feature/serialization-audit`, `feature/caching-optimisation`, `feature/telemetry-plan`, `feature/telemetry-capture` y `feature/telemetry-storage` (local).

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
| **Carga de datos compartida** (`hooks/useAsyncData.ts` y `components/RetryableError.tsx`) — estados de carga, error y reintento de los bloques que piden datos a la API | ✅ Implementado (auditoría de rendimiento, R1 y R2) |
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
| Dominios `auth`, `users` y `profiles` — login JWT, `GET /auth/me`, CRUD de usuarios, `/profiles/me` y `/profiles/{user_id}`, `get_current_user`, `uv run create-admin`; 146 pruebas unitarias en `tests/auth/` (AUTH-088, 88 % de cobertura), más las de integración HTTP en `tests/integration/` | ✅ Implementados en `feature/auth-api`; TinyDB en `storage/auth-db.json` |
| Dominio `inventory` (Hito 5) — ingredientes, entradas y salidas bajo `/api/v1/inventory`; stock calculado (entradas − salidas), 400 ante stock negativo, `user_uuid` del token, sin N+1; `uv run seed-inventory`; 110 pruebas | ✅ Implementado en `feature/inventory-orm`; Supabase (PostgreSQL) con SQLModel |
| Resto de dominios (`locations`, `recruitment`…) | ❌ No iniciado |
| Base de datos | ⏳ Inventario en Supabase (PostgreSQL) con SQLModel desde el Hito 5. `suppliers` e `incidents` siguen en TinyDB provisional. Usuarios y perfiles se quedan en TinyDB (directiva del briefing AUTH-01). Falta la herramienta de migraciones (hoy, `create_all`) |
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
| `app/icon.tsx` — Icono del sitio, generado en el build | ✅ Implementado (auditoría de rendimiento, P3) |
| `components/BrandLogo.tsx` — Logo de las cabeceras | ✅ Implementado (auditoría de rendimiento, R3) |

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
| Docker Compose de desarrollo (`docker-compose.yml`, `uis/Dockerfile`, `services/Dockerfile`; #infra-40) | ✅ Implementado en la rama `feature/dockerize` (fases 0 a 5); solo desarrollo local, sin VPS |
| `scripts/incident-report/` — procesador de reportes de incidentes (Python, sin dependencias, 32 pruebas `unittest`) | ✅ Implementado |
| `internal/` — CLIs internos | ❌ No iniciado |

---

## Propuesta de Próximos Pasos

### Inmediatos (Sprint Actual)

0. **Almacenamiento de eventos de telemetría (rama `feature/telemetry-storage`)** — En curso (2026-11-19). Fases 0 (plan y esquemas), 1 (migración `002_telemetry_events.sql`, que el desarrollador ejecuta en Supabase) y 2 (receptor real) listas. Sigue la verificación de punta a punta. PR contra `feature/telemetry-capture` con el título `feat: telemetry event storage`.

0. **Captura de eventos de telemetría (rama `feature/telemetry-capture`)** — Completada (2026-11-19). El backoffice captura 34 de los 44 eventos del plan (los 6 obligatorios y el piso técnico incluidos) con una única función `track()` y los envía en lotes al receptor provisional `POST /telemetry/events`, verificado en DevTools. PR #22 abierto contra `feature/telemetry-plan`. Siguiente fase de la serie: el receptor real con persistencia en Supabase (en curso, misma URL) y el emisor de la API para los 10 eventos restantes. Divergencias en `docs/BRIEFING_DIVERGENCES.md`, sección 16.

0. **Plan de Telemetría (rama `feature/telemetry-plan`)** — Completado (2026-11-18). La rama sale de `feature/caching-optimisation`; PR #21 abierto contra ella. `docs/telemetry/telemetry-plan.md` y `docs/telemetry/event-schemas.json` (JSON Schema draft-07, validado): 44 eventos (6 obligatorios del briefing y 38 oportunidades en 7 categorías), envelope con los nombres del enunciado, allowlist y datos sensibles por evento, 12 en stream y 32 en batch, throttle en 15, riesgos y exclusiones, y 11 brechas con el modelo actual (precio en las entradas, motivo de merma, mínimos y stock por local, entidad de locales, id de proveedor, cabeceras de correlación…), que son la primera tarea de la fase de captura. Las justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Plan de Telemetría"). Plan en `docs/_private/plan-telemetria.md`.

0. **Estrategia de caching (rama `feature/caching-optimisation`)** — Completada (2026-11-18): `docs/CACHING_REPORT.md` recoge la medición, los 35 endpoints evaluados, las decisiones (caché de 60 s y 5 min en el inventario, modales diferidos, listas de 50 en 50 y `useMemo`), los intercambios y lo que no se cacheó. PR #20 abierto contra `feature/serialization-audit`. Los datos `VOL-` se mantienen hasta que se revise el PR, por si hay que repetir las mediciones; después se retiran con `scripts/seed_volume.py --clear`. Trabajo futuro: paginar `GET /inventory/orders` y `GET /incidents` en la API, y Redis si la API pasa a varios workers. Las justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Estrategia de caching"). Plan en `docs/_private/plan-caching.md`.

0. **Auditoría de serialización (rama `feature/serialization-audit`)** — Completada (2026-11-18): `docs/serialization-audit.md` recoge los 35 endpoints con su estado original y final (todos ✅), los cambios y la verificación. 926 pruebas en la API y una guarda que impide regresiones. PR #19 abierto contra `feature/performance-audit`. Las justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Auditoría de serialización del backend"). Plan en `docs/_private/plan-auditoria-serializacion.md`.

0. **Auditoría de rendimiento (rama `feature/performance-audit`)** — Completada (2026-11-17): `audit/AUDIT.md`, `audit/REPORT.md` y las capturas de `audit/before/` y `audit/after/`. Mejoras medidas: CLS del gestor de incidencias 0,204 → 0 y Best Practices del website 96 → 100. PR #18 abierto contra `feature/dockerize`. Cuando se fusione la cadena y se actualice Next, repetir las mediciones con la misma versión de Lighthouse. Las justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Auditoría de rendimiento de ambos frontends"). Plan en `docs/_private/plan-auditoria-rendimiento.md`.

0. **Contenedorización #infra-40 (rama `feature/dockerize`)** — Completada: `docker compose up` desde la raíz levanta `uis` y `api` con recarga en caliente, verificado (2026-11-17). Un commit por fase (la última, `b1cab16`). PR #17 abierto; desde el 2026-11-18 apunta a `main`. Las justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Contenedorización del monorepo"). Plan en `docs/_private/plan-contenedorizacion.md`.

0. **Hito 5, fase frontend: inventario en el backoffice (rama `feature/inventory-frontend`)** — Fases 0 a 5 y ajustes (pestañas en móvil y Proveedor como lista del directorio) completados y verificados contra una API temporal (2026-11-16). PR #15 fusionado en `main` (2026-11-18). La navegación del backoffice (iconos de la cuenta, menú agrupado y hamburguesa en móvil y tablet) está completa en `feature/backoffice-navigation`, con el PR #16 fusionado en `main` (2026-11-18). Pendiente: cuando se fusionen el #17, el #18 y el #19, actualizar Next por seguridad en el backoffice y el website. Las justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Inventario en el backoffice").

0. **Hito 5: gestión de inventario con ORM (rama `feature/inventory-orm`)** — Completado y verificado en vivo contra Supabase (2026-11-14): dominio `inventory`, semilla cargada y 916 pruebas. PR #14 fusionado en `main` (2026-11-18). Las justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Gestión de inventario con ORM").

0. **AUTH-088: pruebas de la API de autenticación (rama `feature/auth-tests`)** — Núcleo completado (fases 0 a 6; bugs H-1 y H-2 corregidos): 146 pruebas unitarias de autenticación (88 % de cobertura), 55 de Jest y `TESTING.md`. Extras API-042 (101 pruebas, 84 %) y FE-019 (35 pruebas de Jest) completados. PR #13 fusionado en `main` (2026-11-18). Las justificaciones están en `docs/BRIEFING_DIVERGENCES.md` (sección "Batería de pruebas de autenticación").

0. **Entregar la auditoría de gestión de errores (rama `feature/error-handling-audit`)** — Los 29 hallazgos están corregidos, verificados y documentados (2026-11-09). Commit de cierre `d8f39c2`; PR #12 fusionado en `main` (2026-11-18). La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Auditoría de gestión de errores").

0. **Entregar el gestor de incidencias (rama `feature/incident-manager`)** — Implementado, verificado, documentado y con commit (`ccd09cc`). PR #11 fusionado en `main` (2026-11-18). La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Gestor de incidencias centralizado").

0. **Entregar AUTH-03 (rama `feature/password-reset`)** — Implementado, verificado y documentado. Commits `e87121c` y `2906225`; PR #10 fusionado en `main` (2026-11-18). La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Recuperación y cambio de contraseña", con la verificación de los 12 criterios).

0. **Entregar AUTH-02 (rama `feature/auth-frontend`)** — Implementado, verificado, documentado y con commit (`fb35b8d`). PR #9 fusionado en `main` (2026-11-18). La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Autenticación en el frontend").

0. **Entregar AUTH-01 (rama `feature/auth-api`)** — Implementado, verificado y documentado. PR #8 fusionado en `main` (2026-11-18). La entrega debe incluir las justificaciones de `docs/BRIEFING_DIVERGENCES.md` (sección "Autenticación y protección de rutas").

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
   - ✅ Desplegar en entorno local con Docker (#infra-40, `docker compose up` desde la raíz).

5. **Migración de utilidades core** — Portar a Python, dominio por dominio, las reglas de `packages/brasa-core`. Decisión tomada: el backend es la fuente de verdad. Al terminar, retirar `/funciones` o hacer que llame a la API, y eliminar el paquete junto con su configuración en `uis/backoffice`.

6. **Pipeline de datos** — Poblar `data/` con datasets realistas de Brasaland y crear pipelines ETL básicos. Ya hay un primer dataset (`data/raw/incidents-brasaland.csv`) con su procesador en `scripts/incident-report/`; sus reglas de validación servirán de referencia para la ingesta de incidentes del dashboard operativo.

### Mediano Plazo

7. **Agente de formación y recetario** — Desarrollar el agente principal enfocado en el área de Formación y Estándares de Calidad (prioridad personal del proyecto), integrando el skill del paso 2.

8. **Sistema de fidelización** — Implementar el módulo de "Brasa Points" digital con CRM de clientes.

9. **Dashboard operativo** — Tablero en tiempo real para Operaciones de Restaurante con alertas inteligentes.

10. **Workflows de automatización** — Flujos n8n para orquestación de procesos cross-sistema (ej. notificaciones, reportes semanales).

---

## Riesgos y Bloqueantes

- **Backend incipiente**: solo existen los dominios `incidents` (su último análisis vive en memoria), `suppliers` (TinyDB provisional), `inventory` (Supabase) y la autenticación JWT. El tracker sigue usando la API de playground.
- **Base de datos a medio migrar**: el inventario ya está en Supabase (PostgreSQL) con SQLModel, pero `suppliers` e `incidents` siguen en TinyDB, que no está pensado para muchos procesos escribiendo a la vez. Faltan las migraciones de esquema: `create_all` solo crea tablas nuevas, así que cambiar una tabla existente exige hacerlo a mano en Supabase.
- **Inventario con stock global**: el stock no se parte por local (decisión D7). Cuando exista `locations/`, habrá que decidir si pasa a calcularse por local.
- **`suppliers` frente a `procurement`**: la propuesta reservaba los proveedores para `procurement/`. Cuando se aborden el historial de precios y las compras, hay que integrar ambos dominios para que solo uno sea dueño de los proveedores (propuesta, 2.7).
- **Dependencia de Python para agentes**: el esqueleto está en Python, pero el resto del stack es TypeScript/JavaScript — se debe decidir si los agentes serán Python puro o se integran vía MCP/subprocess.
- **Sin gestor de monorepo**: no hay `package.json` raíz ni scripts compartidos; cada proyecto se gestiona independientemente.
- **Website no publicable aún**: el envío del formulario es simulado, faltan los términos del programa y las sedes usan datos de ejemplo. El detalle está en `uis/website/README.es.md`.
- **Sesión del backoffice con límites conocidos** (AUTH-02):
  - el token vive en `localStorage`, como exige el ticket, así que un script inyectado podría leerlo (la propuesta 5.2 preveía una cookie `httpOnly`);
  - el registro es abierto, así que cualquiera puede crearse una cuenta `user`, y no hay permisos por herramienta;
  - la comprobación de sesión es del navegador; la protección de los datos está en la API.
- **Next.js vulnerable en las dos aplicaciones** (`npm audit`, 2026-11-10): `uis/backoffice` y `uis/website` usan `next` 16.3.5, con avisos críticos de ejecución remota de código (optimización de imágenes con SVG, `use cache`, `next/og`) y otros altos (SSRF, DoS, envenenamiento de caché). El arreglo es `next` y `eslint-config-next` 16.4.6, sin cambio de versión mayor, más `npm audit fix` sin `--force` para `sharp`, `zod` y `source-map-js` (dependencias indirectas). **Decisión:** hacerlo en una rama propia desde `main` cuando no quede ningún PR de la cadena pendiente de fusionar, y verificar `lint`, `build`, pruebas y las vistas principales de las dos aplicaciones. Hasta entonces, no desplegar ninguna de las dos. Los avisos bajos y moderados que añadió Jest (AUTH-088) son solo de desarrollo.
- **Dependencia temporal del backoffice**: mientras exista `packages/brasa-core`, se construye desde la raíz del repositorio, y los cambios en el paquete también deben comprobar `uis/backoffice`.

---

_Actualizado: 2026-11-17_