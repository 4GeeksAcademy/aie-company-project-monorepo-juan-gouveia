# Proyecto de Compañía - Ingeniería de IA — Plantilla para estudiantes

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

_Plantilla base para proyectos transversales del Programa de Carrera en Ingeniería de IA — 4Geeks Academy._

_These instructions are also available in [English](./README.md)._

---

## Propósito

Este repositorio es la **plantilla de inicio** para los proyectos transversales. Trabajarás con escenarios de empresas reales (Brasaland, TrackFlow, Nexova) construyendo entregables que se corresponden con los hitos del curso (Web, Programación, Backend, Telemetría, RAG, Agentes, Workflows, Tiempo real).

- Crea una plantilla a partir de este repositorio.
- Reemplaza el `CONTEXT.md` placeholder por el contexto de tu empresa asignada.
- Usa `skills/` y los `README.md` por carpeta como guía de trabajo.

---

## Cómo empezar

1. **Usa este repositorio como plantilla** y crea tu propio repo de proyecto.
2. **Clona** tu repositorio (o ábrelo en Codespaces).
3. **Reemplaza** `CONTEXT.md` con el contexto completo de tu empresa asignada.
4. **Lee esta guía de carpetas** y abre el `README.md` de la carpeta en la que estés trabajando.
5. **Empieza a implementar** en la carpeta correcta — no tires todo en la raíz.
6. **Documenta** lo que añadas: cada app, servicio, agente o pipeline nuevo lleva subcarpeta + README.

---

## Cómo entender este monorepo

Estás construyendo **una sola empresa** a lo largo de muchos hitos y proyectos. Cada carpeta de primer nivel tiene **una responsabilidad clara** — como en un repositorio real de un equipo de ingeniería.

| Capa                    | Carpetas                          | Qué vive aquí                                                               |
| ----------------------- | --------------------------------- | --------------------------------------------------------------------------- |
| **Contexto de empresa** | `CONTEXT.md`                      | Datos del dominio, nombres de campos y restricciones de tu empresa asignada |
| **Cara al usuario**     | `uis/`, `services/`               | Frontends y backends con los que interactúan usuarios u operadores          |
| **Datos**               | `data/`                           | Archivos crudos, pipelines, datasets procesados y conjuntos de evaluación   |
| **IA**                  | `agents/`, `skills/`, `mcps/`     | Agentes, capacidades reutilizables para agentes y servidores MCP            |
| **Automatización**      | `workflows/`                      | Flujos n8n y orquestación entre sistemas                                    |
| **Reutilización**       | `packages/`, `shared/`            | Tipos compartidos, SDKs, esquemas, plantillas                               |
| **Operaciones**         | `infra/`, `scripts/`, `internal/` | Docker, despliegue, scripts puntuales, CLIs internas                        |
| **Documentación**       | `docs/`                           | Arquitectura, decisiones y convenciones de todo el repo                     |

**Regla rápida:** si tiene interfaz visual → `uis/`. Si expone una API o corre en segundo plano → `services/`. Si mueve o transforma datos → `data/`. Si el trabajo lo hace un modelo de IA → `agents/` (+ `skills/` o `mcps/` según haga falta).

---

## Estado actual del proyecto

Este repositorio contiene el proyecto de **Brasaland**. `CONTEXT.md` (y su versión en español, `CONTEXT.es.md`) recoge el briefing de la empresa, y [`memory-bank/progress.md`](./memory-bank/progress.md) lleva el estado detallado y los próximos pasos.

| Área | Ruta | Estado |
| --- | --- | --- |
| Web corporativa | [`uis/website/`](./uis/website/README.es.md) | App Next.js en el puerto 3000. El envío del formulario de Brasa Points es simulado |
| Backoffice | [`uis/backoffice/`](./uis/backoffice/README.es.md) | App Next.js en el puerto 3001: Talent Pipeline Tracker (`/talento`), análisis de incidencias (`/incidencias`), directorio de proveedores (`/proveedores`) y pruebas de funciones (`/funciones`). Exige sesión en todas las vistas salvo `/login` y `/register` (token JWT en `localStorage`) |
| API de Brasaland | [`services/brasaland-api/`](./services/brasaland-api/README.es.md) | FastAPI, organizada por dominios. Implementa `incidents` y `suppliers` (este último con TinyDB provisional), y la autenticación JWT (`auth`, `users` y `profiles`) |
| Script de reporte de incidentes | [`scripts/incident-report/`](./scripts/incident-report/README.es.md) | CLI en Python que valida y resume el CSV de incidentes y exporta `data/process/results.csv`. Reutiliza la lógica de análisis de la API |
| Paquetes compartidos | [`packages/`](./packages/README.es.md) | `@repo/brasa-core` es transitorio (lo usa `/funciones`); `@repo/shared-types` aún no tiene consumidores |
| Datos | [`data/raw/`](./data/raw/README.es.md) | `incidents-brasaland.csv` (100 incidentes de prueba) |
| IA, automatización e infraestructura | `agents/`, `skills/`, `mcps/`, `workflows/`, `infra/` | Solo la estructura y los ejemplos de la plantilla |

- Las instrucciones para agentes de código están en el [`AGENTS.md`](./AGENTS.md) raíz, con reglas y skills de desarrollo en `.agents/`.
- Toda la plataforma se ejecuta en Docker con un solo comando (ver [Ejecutar con Docker](#ejecutar-con-docker)). Cada proyecto también se puede instalar y ejecutar desde su carpeta, siguiendo su README. No hay runner de workspace.

---

## Ejecutar con Docker

El entorno de desarrollo está definido en [`docker-compose.yml`](./docker-compose.yml) (ticket #infra-40): dos contenedores en la red `brasaland-net`, con recarga en caliente y el código montado desde el host.

**Requisitos:** Docker Desktop, o Docker Engine con el plugin Compose v2. No hace falta tener Node ni Python en la máquina.

```bash
cp .env.example .env   # una vez: rellena los secretos (SECRET_KEY, DATABASE_URL, RESEND_API_KEY)
docker compose up      # añade -d para dejarlo en segundo plano
```

Crear el `.env` es el único paso manual: los secretos no pueden estar en Git. Si falta `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` o `DATABASE_URL`, Compose se detiene y dice cuál. El `.env` está ignorado por Git.

| Servicio | Contenido | URL desde el host |
| --- | --- | --- |
| `uis` | `uis/website` y `uis/backoffice` (`next dev`), lanzados por [`uis/start.sh`](./uis/start.sh) | http://localhost:3000 y http://localhost:3001 |
| `api` | `services/brasaland-api` (Uvicorn con `--reload`) | http://localhost:8000 (documentación en `/docs`) |

- **Las llamadas entre servicios usan el nombre del servicio.** El intermediario (BFF) del backoffice llama a `http://api:8000/api/v1` (`API_BASE_URL`). Las URL que usa el navegador (`NEXT_PUBLIC_API_BASE_URL`, `FRONTEND_URL`) siguen siendo de `localhost`.
- **Recarga en caliente:** el código está montado con bind mounts, así que los cambios en el host se ven sin reconstruir. Docker Desktop no propaga los eventos de archivos de Windows ni de macOS, así que los dos servicios vigilan los cambios por sondeo (`NEXT_WATCH_POLL_INTERVAL_MS`, `WATCHFILES_FORCE_POLLING`). En Docker, Next.js corre con webpack (`next dev --webpack`) porque Turbopack no detecta los cambios en los bind mounts; fuera de Docker, `npm run dev` sigue con Turbopack.
- **Datos:** los archivos TinyDB de `services/brasaland-api/storage/` son los mismos que usa la API fuera de Docker. El inventario está en Supabase, fuera del stack.
- **Cada servicio recibe solo sus variables**, interpoladas desde el `.env`. Next.js también carga `uis/backoffice/.env.local` desde la carpeta montada, pero las variables de Compose tienen prioridad.

Comandos útiles (desde la raíz del repositorio):

| Tarea | Comando |
| --- | --- |
| Estado y logs | `docker compose ps` · `docker compose logs -f api` |
| Parar | `docker compose down` (con `-v` también borra los volúmenes de los contenedores) |
| Tras cambiar dependencias (`package-lock.json`, `requirements.txt`) | `docker compose up --build --renew-anon-volumes` |
| Terminal en un contenedor | `docker compose exec api sh` · `docker compose exec uis sh` |
| Sembrar el directorio de proveedores | `docker compose exec api python -m app.domains.suppliers.seed` |
| Crear el primer administrador (interactivo) | `docker compose exec api python -c "import sys; from app.domains.users.create_admin import run; sys.exit(run())"` |
| Sembrar el inventario (Supabase) | `docker compose exec api python -c "import sys; from app.domains.inventory.seed import main; sys.exit(main())"` |

La imagen de la API instala sus dependencias desde [`services/requirements.txt`](./services/requirements.txt), generado desde `uv.lock`. Si cambian las dependencias de la API, hay que regenerarlo como indica su cabecera. Los paquetes locales `packages/shared` y `packages/brasa-core` llegan a las imágenes como `additional_contexts` de Compose. El despliegue a un servidor de producción queda fuera de alcance: ver [`docs/BRIEFING_DIVERGENCES.md`](./docs/BRIEFING_DIVERGENCES.md#contenedorización-del-monorepo).

---

## Guía de carpetas — qué va en cada una

Lee el `README.md` enlazado dentro de cada carpeta antes de empezar a programar ahí.

### Archivos en la raíz

| Ruta                         | Propósito                                                            | Qué haces aquí                                                                                               |
| ---------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| [`CONTEXT.md`](./CONTEXT.md) | Fuente única de verdad de tu empresa (Brasaland, TrackFlow o Nexova) | **Primer paso:** copia aquí el briefing de tu empresa para que apps, agentes y prompts usen el mismo dominio |
| `docker-compose.yml`         | Orquestación local de todo el stack                                  | Mantener en la raíz del repo — conecta `services/`, bases de datos y otros contenedores desde un solo lugar  |
| `README.md` / `README.es.md` | Esta guía                                                            | Orientación — estás aquí                                                                                     |

### `uis/` — interfaces de usuario

**Propósito:** Todas las aplicaciones frontend — todo lo que un humano ve y en lo que hace clic.

**Pon aquí:**

- Sitio web público (`website/`)
- Admin interno / backoffice (`backoffice/`)
- Portales de clientes, apps de fidelización, herramientas Streamlit/Gradio, dashboards con UI

**Ejemplos:** landing corporativa, backoffice de operaciones, portal de fidelización, UI de dashboard de telemetría

→ Ver [`uis/README.md`](./uis/README.md)

### `services/` — API centralizada de la empresa (FastAPI)

**Propósito:** Un **backend FastAPI centralizado** para toda la empresa — un solo punto de entrada que reduce la complejidad a medida que crece el proyecto.

**Pon aquí:**

- Una app FastAPI principal (p. ej. `api/`) con routers/módulos por dominio (ubicaciones, menús, ventas, telemetría, etc.)
- Workers en background solo cuando de verdad necesiten correr separados de la API

**Recomendación:** evita dividir en muchos microservicios al inicio. Añade endpoints a la misma app FastAPI; extrae un worker solo cuando sea necesario.

**Ejemplos:** `/locations`, `/menus`, `/sales/reports`, webhooks, jobs programados

→ Ver [`services/README.md`](./services/README.md)

### `data/` — datasets, pipelines y evaluación

**Propósito:** Todo lo relacionado con datos, desde archivos crudos hasta tablas listas para producción.

| Subcarpeta                                      | Propósito                     | Qué haces aquí                                                                  |
| ----------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------- |
| [`data/raw/`](./data/raw/README.md)             | Datos fuente sin tocar        | Guardar dumps, exports, CSV/JSON de ejemplo — documentar origen y reglas de PII |
| [`data/pipelines/`](./data/pipelines/README.md) | Jobs ETL/ELT                  | Escribir scripts de ingesta, limpieza y transformación                          |
| [`data/process/`](./data/process/README.md)     | Salidas limpias / intermedias | Guardar artefactos de pipelines (features, agregados, tablas limpias)           |
| [`data/eval/`](./data/eval/README.md)           | Medición de calidad           | Golden sets, datasets de evaluación RAG/agentes, métricas de experimentos       |

**Flujo:** `raw` → `pipelines` → `process` → consumido por `services/`, `uis/` o `agents/`. Usa `eval` para demostrar calidad.

### `agents/` — agentes de IA

**Propósito:** Asistentes de IA autónomos o semi-autónomos para la empresa.

**Pon aquí:**

- Una subcarpeta por agente (p. ej. `support-agent/`, `onboarding-agent/`)
- Config del agente, prompts, herramientas, tests
- Empieza desde [`agents/_template/`](./agents/_template/README.md) al crear un agente nuevo

**Ejemplos:** bot de soporte al cliente, copiloto de onboarding, asistente de formación

→ Ver [`agents/README.md`](./agents/README.md)

### `skills/` — capacidades reutilizables para agentes

**Propósito:** Instrucciones empaquetadas + scripts que agentes (o tú en Cursor) reutilizan en todo el repo.

**Pon aquí:**

- Skills de análisis de datos, code review, scraping, investigación, etc.
- Cada skill = carpeta con `SKILL.md`, scripts y recursos opcionales

**Ejemplo incluido:** `skills/data-analysis/` (script de limpieza pandas + referencia de métricas)

→ Ver [`skills/README.md`](./skills/README.md)

### `mcps/` — servidores Model Context Protocol

**Propósito:** Conectar modelos de IA con tus sistemas — bases de datos, APIs, GitHub, herramientas propias.

**Pon aquí:**

- Una subcarpeta por servidor MCP (p. ej. `database-mcp/`, `github-mcp/`)
- Definiciones de tools, resources y config del servidor

**Cuándo usarlo:** cuando un agente necesita acceso en vivo a datos o acciones que el código solo no puede dar

→ Ver [`mcps/README.md`](./mcps/README.md)

### `workflows/` — automatización y orquestación

**Propósito:** Conectar sistemas sin escribir apps completas — jobs programados, webhooks, notificaciones.

**Pon aquí:**

- Exports de workflows n8n, configs de Make/Zapier u orquestación documentada
- Flujos que enlazan `services/`, `data/pipelines/` y `agents/`

**Ejemplos:** nuevo pedido → alerta Slack, trigger ETL nocturno, lead → sync CRM

→ Ver [`workflows/README.md`](./workflows/README.md)

### `packages/` — librerías compartidas

**Propósito:** Código versionable reutilizado por varias apps, agentes o pipelines.

**Pon aquí:**

- Tipos TypeScript compartidos (`packages/shared/` → `@repo/shared-types`)
- Librerías de componentes UI, clientes API, SDKs de analytics

**Regla:** si `uis/` y `services/` comparten la misma interfaz → extráela aquí

→ Ver [`packages/README.md`](./packages/README.md)

### `shared/` — recursos sueltos compartidos

**Propósito:** Recursos que no son un paquete completo — esquemas, plantillas, assets estáticos, docs cortas.

**Pon aquí:**

- Esquemas JSON, plantillas de email, specs OpenAPI, design tokens
- Cualquier cosa reutilizada pero demasiado pequeña o no-código para `packages/`

→ Ver [`shared/README.md`](./shared/README.md)

### `docs/` — documentación transversal

**Propósito:** Arquitectura y decisiones que abarcan todo el proyecto de la empresa.

**Pon aquí:**

- Diagramas de arquitectura, ADRs, guías de seguridad/observabilidad
- Convenciones no atadas a una sola app o agente

→ Ver [`docs/README.md`](./docs/README.md)

### `infra/` — infraestructura y despliegue

**Propósito:** Cómo corre el proyecto en Docker, cloud o CI.

**Pon aquí:**

- Dockerfiles, Terraform, manifiestos K8s, configs Nginx, pipelines CI/CD

**Mantener en la raíz del repo:** `docker-compose.yml` — orquesta el entorno local de `services/`, bases de datos y otros contenedores desde un solo lugar.

→ Ver [`infra/README.md`](./infra/README.md)

### `scripts/` — scripts de ayuda

**Propósito:** Automatización pequeña y repetible — no apps completas.

**Pon aquí:**

- Scripts de setup, generadores de seed data, wrappers de lint, migraciones puntuales
- Documenta cada script: qué hace, argumentos y cómo ejecutarlo

**Diferencia con `internal/`:** los scripts suelen ser archivos sueltos; las tools de `internal/` son proyectos estructurados con deps y tests propios.

→ Ver [`scripts/README.md`](./scripts/README.md)

### `internal/` — herramientas internas para desarrolladores

**Propósito:** Utilidades robustas para el equipo de ingeniería.

**Pon aquí:**

- CLIs, herramientas de migración empaquetadas, evaluadores de prompts
- Tools con su propio `package.json`, tests y pasos de instalación

→ Ver [`internal/README.md`](./internal/README.md)

---

## ¿Dónde pongo esto?

Guía rápida de decisión:

```text
¿Tiene botones y pantallas?                → uis/
¿Corre en servidor / API / cola?           → services/
¿Es dato crudo o transformado?             → data/raw/ o data/process/
¿Mueve datos entre sistemas?               → data/pipelines/
¿Mides calidad de IA/pipelines?            → data/eval/
¿Es un asistente de IA con un objetivo?    → agents/
¿Es una capacidad/instrucción reutilizable?→ skills/
¿La IA necesita llamar tools/APIs externas?→ mcps/
¿Es n8n / automatización programada?       → workflows/
¿2+ carpetas importan el mismo código?     → packages/
¿Es esquema/plantilla/asset, no librería?  → shared/
¿Es arquitectura o docs de todo el equipo? → docs/
¿Es docker-compose para dev local?         → raíz del repo
¿Es Docker / deploy / config cloud?        → infra/
¿Es un script puntual?                     → scripts/
¿Es una CLI con su propio paquete?         → internal/
```

---

## Estructura del repositorio (árbol)

```text
ai-engineering-company-project-monorepo/
├── README.md / README.es.md   # Esta guía
├── AGENTS.md                  # Instrucciones para agentes de código (+ reglas y skills en .agents/)
├── CONTEXT.md / CONTEXT.es.md # Briefing de Brasaland
├── company-choice.md          # Elección de empresa y enfoque personal
├── memory-bank/               # Brief, contexto técnico y progreso del proyecto
├── docker-compose.yml         # ← Orquestación local (raíz del repo; aún no creado)
├── uis/                       # Frontends (website, backoffice, dashboards)
├── services/                  # API FastAPI centralizada de la empresa
├── data/
│   ├── raw/                   # Datasets fuente
│   ├── pipelines/             # Jobs ETL/ELT
│   ├── process/               # Salidas limpias / intermedias
│   └── eval/                  # Conjuntos de evaluación y métricas
├── agents/                    # Agentes de IA (+ plantilla _template/)
├── skills/                    # Skills reutilizables para agentes
├── mcps/                      # Servidores MCP para acceso a tools
├── workflows/                 # Flujos n8n y automatizaciones
├── packages/                  # Librerías compartidas (@repo/shared-types, …)
├── shared/                    # Esquemas, plantillas, assets sueltos
├── docs/                      # Arquitectura y docs transversales
├── infra/                     # Docker, Terraform, despliegue
├── scripts/                   # Scripts de ayuda
└── internal/                  # CLIs y herramientas internas de desarrollo
```

---

## Enlaces

- [4Geeks Academy — Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [Cómo empezar un proyecto de código](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contribuidores

Esta plantilla fue creada como parte del Programa de Carrera de Ingeniería de IA de 4Geeks Academy por [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) y [@alezanchezr](https://x.com/alesanchezr), junto a otros muchos colaboradores. Descubre más sobre nuestro [Curso de Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia) y sobre [otros cursos](https://4geeksacademy.com/es/comparar-programas).

Puedes encontrar otras plantillas y recursos similares en la [página de GitHub de 4Geeks Academy](https://github.com/4geeksacademy).

_Esta plantilla la mantiene 4Geeks Academy para el track de Ingeniería de IA. Uso exclusivo del programa._
