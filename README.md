# AI Engineering Company Project — Student Template

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

_Base template for transversal projects in the AI Engineering Career Program — 4Geeks Academy._

_Estas instrucciones tambien estan disponibles en [espanol](./README.es.md)._

---

## Purpose

This repository is the **starter template** for transversal projects. You will work on real company scenarios (Brasaland, TrackFlow, Nexova), building deliverables that map to course milestones (Web, Programming, Backend, Telemetry, RAG, Agents, Workflows, Real-time).

- Create a template from this repository.
- Replace the placeholder `CONTEXT.md` with your assigned company context.
- Use `skills/` and the directory-level `README.md` files as working guidance.

---

## How to start

1. **Use this repository as a template** and create your own project repo.
2. **Clone** your repository (or open it in Codespaces).
3. **Replace** `CONTEXT.md` with the full context for your assigned company.
4. **Read this folder guide** and open the `README.md` of the folder you are working in.
5. **Start implementing** in the right folder — do not dump everything in the root.
6. **Document** what you add: each new app, service, agent, or pipeline gets a subfolder + README.

---

## How to think about this monorepo

You are building **one company** across many milestones and projects. Each top-level folder has a **single responsibility** — like a real engineering team repo.

| Layer               | Folders                           | What lives here                                                  |
| ------------------- | --------------------------------- | ---------------------------------------------------------------- |
| **Company context** | `CONTEXT.md`                      | Domain facts, field names, constraints for your assigned company |
| **User-facing**     | `uis/`, `services/`               | Frontends and backends users (or operators) interact with        |
| **Data**            | `data/`                           | Raw files, pipelines, processed datasets, evaluation sets        |
| **AI**              | `agents/`, `skills/`, `mcps/`     | Agents, reusable agent capabilities, MCP tool servers            |
| **Automation**      | `workflows/`                      | n8n flows and cross-system orchestration                         |
| **Reuse**           | `packages/`, `shared/`            | Shared types, SDKs, schemas, templates                           |
| **Operations**      | `infra/`, `scripts/`, `internal/` | Docker, deploy configs, one-off scripts, internal CLIs           |
| **Documentation**   | `docs/`                           | Architecture, decisions, conventions for the whole repo          |

**Rule of thumb:** if it has a UI → `uis/`. If it exposes an API or runs in the background → `services/`. If it moves or transforms data → `data/`. If an AI model does the work → `agents/` (+ `skills/` or `mcps/` as needed).

---

## Current status of the project

This repository holds the **Brasaland** project. `CONTEXT.md` (and its Spanish version, `CONTEXT.es.md`) contains the company briefing, and [`memory-bank/progress.md`](./memory-bank/progress.md) tracks the detailed status and next steps.

| Area | Path | Status |
| --- | --- | --- |
| Corporate website | [`uis/website/`](./uis/website/README.md) | Next.js app on port 3000. The Brasa Points sign-up form submission is simulated |
| Backoffice | [`uis/backoffice/`](./uis/backoffice/README.md) | Next.js app on port 3001: Talent Pipeline Tracker (`/talento`), incident analysis (`/incidencias`), supplier directory (`/proveedores`) and business-function tests (`/funciones`). Every view requires a session except `/login` and `/register` (JWT in `localStorage`) |
| Brasaland API | [`services/brasaland-api/`](./services/brasaland-api/README.md) | FastAPI, organized by domain. It implements `incidents` and `suppliers` (the latter with temporary TinyDB storage), plus JWT authentication (`auth`, `users` and `profiles`) |
| Incident report script | [`scripts/incident-report/`](./scripts/incident-report/README.md) | Python CLI that validates and summarizes the incidents CSV and exports `data/process/results.csv`. It reuses the API's analysis logic |
| Shared packages | [`packages/`](./packages/README.md) | `@repo/brasa-core` is transitional (used by `/funciones`); `@repo/shared-types` has no consumers yet |
| Data | [`data/raw/`](./data/raw/README.md) | `incidents-brasaland.csv` (100 test incidents) |
| Business pipeline | [`data/pipelines/`](./data/pipelines/README.md), [`data/process/`](./data/process/README.md) and [`services/reporting/`](./services/reporting/README.md) | Prefect flow that recomputes the weekly cost and waste report per location every night, launched by the [nightly script](./scripts/README.md), into `reporting.weekly_location_performance` (Supabase), in subflows; its three endpoints under `/reporting`; the backoffice dashboard [`/reporte-semanal`](./uis/backoffice/README.md#tools), and the unit tests of its tasks in [`tests/pipelines/`](./tests/pipelines/README.md) ([design](./data/pipelines/PIPELINE_DESIGN.md), in Spanish) |
| Nightly telemetry script | [`scripts/nightly_export.py`](./scripts/README.md#nightly_exportpy) and [`services/jobs/`](./services/jobs/README.md) | Every night (`nightly-scheduler` service, `0 8 * * *` UTC) it exports the previous day's telemetry to CSV in `data/raw/telemetry_exports/`, launches the business pipeline and records the execution in `ops.job_runs` (`pending → processing → completed \| failed`), with `processing` as the lock and per-date idempotency |
| AI, automation and infrastructure | `agents/`, `skills/`, `mcps/`, `workflows/`, `infra/` | Template structure and examples only |

- Instructions for coding agents are in the root [`AGENTS.md`](./AGENTS.md), with development rules and skills in `.agents/`.
- The whole platform runs in Docker with one command (see [Running with Docker](#running-with-docker)). Each project can also be installed and run from its own folder, following its README. There is no workspace runner.

---

## Running with Docker

The development environment is defined in [`docker-compose.yml`](./docker-compose.yml) (ticket #infra-40): four containers on the `brasaland-net` network, with hot reload and the source code mounted from the host.

**Requirements:** Docker Desktop, or Docker Engine with the Compose v2 plugin. You do not need Node or Python on your machine.

```bash
cp .env.example .env   # once: fill in the secrets (SECRET_KEY, DATABASE_URL, RESEND_API_KEY)
docker compose up      # add -d to run in the background
```

Creating `.env` is the only manual step: secrets cannot live in Git. If `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` or `DATABASE_URL` is missing, Compose stops and says which one. `.env` is ignored by Git.

| Service | Contents | URL from the host |
| --- | --- | --- |
| `uis` | `uis/website` and `uis/backoffice` (`next dev`), started by [`uis/start.sh`](./uis/start.sh) | http://localhost:3000 and http://localhost:3001 |
| `api` | `services/brasaland-api` (Uvicorn with `--reload`) | http://localhost:8000 (docs at `/docs`) |
| `prefect-server` | Prefect server (`prefecthq/prefect:3.9.4-python3.12`) | http://localhost:4200 |
| `reporting-pipeline` | The business pipeline serving its deployment for the API's manual runs (`data/pipelines/pipeline.py --serve`). It reads its connection from `data/pipelines/.env` (optional: without it, runs fail for lack of a connection) | — |
| `nightly-scheduler` | The nightly telemetry script ([`scripts/nightly_export.py`](./scripts/nightly_export.py)), launched by supercronic every day at 08:00 UTC ([`scripts/nightly_export.crontab`](./scripts/nightly_export.crontab)): it exports the previous day's telemetry to CSV and launches the pipeline's scheduled run. It reads `services/jobs/.env` and `data/pipelines/.env` (optional: without them, the run fails with a message) | — |

- **Service-to-service calls use the service name.** The backoffice proxy (BFF) calls `http://api:8000/api/v1` (`API_BASE_URL`). URLs used by the browser (`NEXT_PUBLIC_API_BASE_URL`, `FRONTEND_URL`) stay as `localhost` URLs.
- **Hot reload:** the code is bind-mounted, so changes on the host show up without rebuilding. Docker Desktop does not forward file events from Windows or macOS, so both services poll for changes (`NEXT_WATCH_POLL_INTERVAL_MS`, `WATCHFILES_FORCE_POLLING`). In Docker, Next.js runs with webpack (`next dev --webpack`) because Turbopack does not detect changes on bind mounts; outside Docker, `npm run dev` still uses Turbopack.
- **Data:** the TinyDB files in `services/brasaland-api/storage/` are the same ones the API uses outside Docker. The inventory is in Supabase, outside the stack.
- **Each service gets only its own variables**, interpolated from `.env`. Next.js also loads `uis/backoffice/.env.local` from the mounted folder, but Compose's variables take precedence.

Useful commands (from the repository root):

| Task | Command |
| --- | --- |
| Status and logs | `docker compose ps` · `docker compose logs -f api` |
| Stop | `docker compose down` (add `-v` to also remove the container volumes) |
| After changing dependencies (`package-lock.json`, `requirements.txt`) | `docker compose up --build --renew-anon-volumes` |
| Shell in a container | `docker compose exec api sh` · `docker compose exec uis sh` |
| Seed the supplier directory | `docker compose exec api python -m app.domains.suppliers.seed` |
| Create the first admin (interactive) | `docker compose exec api python -c "import sys; from app.domains.users.create_admin import run; sys.exit(run())"` |
| Seed the inventory (Supabase) | `docker compose exec api python -c "import sys; from app.domains.inventory.seed import main; sys.exit(main())"` |

The API image installs its dependencies from [`services/requirements.txt`](./services/requirements.txt), generated from `uv.lock`. After changing the API's dependencies, regenerate it as its header explains. The local packages `packages/shared` and `packages/brasa-core` reach the images as Compose `additional_contexts`. Deploying to a production server is out of scope: see [`docs/BRIEFING_DIVERGENCES.md`](./docs/BRIEFING_DIVERGENCES.md#contenedorización-del-monorepo).

---

## Folder guide — what goes where

Read the linked `README.md` inside each folder before you start coding there.

### Root files

| Path                         | Purpose                                                                   | What you do here                                                                                              |
| ---------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| [`CONTEXT.md`](./CONTEXT.md) | Single source of truth for your company (Brasaland, TrackFlow, or Nexova) | **First step:** copy your assigned company briefing here so every app, agent, and prompt uses the same domain |
| `docker-compose.yml`         | Local dev orchestration for the whole stack                               | Keep at repo root — wires `services/`, databases, and other containers from one place                         |
| `README.md` / `README.es.md` | This guide                                                                | Orientation — you are here                                                                                    |

### `uis/` — user interfaces

**Purpose:** All frontend applications — anything a human sees and clicks.

**Put here:**

- Public website (`website/`)
- Internal admin / backoffice (`backoffice/`)
- Customer portals, loyalty apps, Streamlit/Gradio tools, dashboards with a UI

**Examples:** corporate landing page, operations backoffice, loyalty portal, telemetry dashboard UI

→ See [`uis/README.md`](./uis/README.md)

### `services/` — centralized company API (FastAPI)

**Purpose:** One **centralized FastAPI backend** for the whole company — a single entry point that keeps complexity low as the project grows.

**Put here:**

- One main FastAPI app (e.g. `api/`) with routers/modules per domain (locations, menus, sales, telemetry, etc.)
- Background workers only when they truly need to run separately from the API

**Recommendation:** avoid splitting into many microservices early. Add endpoints to the same FastAPI app; extract a worker only when necessary.

**Examples:** `/locations`, `/menus`, `/sales/reports`, webhook handlers, scheduled jobs

→ See [`services/README.md`](./services/README.md)

### `data/` — datasets, pipelines, and evaluation

**Purpose:** Everything data-related, from raw files to production-ready tables.

| Subfolder                                       | Purpose                      | What you do here                                                          |
| ----------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------- |
| [`data/raw/`](./data/raw/README.md)             | Untouched source data        | Store dumps, exports, sample CSVs/JSON — document origin and PII rules    |
| [`data/pipelines/`](./data/pipelines/README.md) | ETL/ELT jobs                 | Write ingestion, cleaning, and transformation scripts                     |
| [`data/process/`](./data/process/README.md)     | Clean / intermediate outputs | Save artifacts produced by pipelines (features, aggregates, clean tables) |
| [`data/eval/`](./data/eval/README.md)           | Quality measurement          | Golden sets, RAG/agent eval datasets, experiment metrics                  |

**Flow:** `raw` → `pipelines` → `process` → consumed by `services/`, `uis/`, or `agents/`. Use `eval` to prove quality.

### `agents/` — AI agents

**Purpose:** Autonomous or semi-autonomous AI assistants for the company.

**Put here:**

- One subfolder per agent (e.g. `support-agent/`, `onboarding-agent/`)
- Agent config, prompts, tools wiring, tests
- Start from [`agents/_template/`](./agents/_template/README.md) when creating a new agent

**Examples:** customer support bot, employee onboarding copilot, training assistant

→ See [`agents/README.md`](./agents/README.md)

### `skills/` — reusable agent capabilities

**Purpose:** Packaged instructions + scripts that agents (or you in Cursor) reuse across the repo.

**Put here:**

- Skills for data analysis, code review, scraping, research, etc.
- Each skill = a folder with `SKILL.md`, optional scripts and resources

**Example included:** `skills/data-analysis/` (pandas cleaning script + metrics reference)

→ See [`skills/README.md`](./skills/README.md)

### `mcps/` — Model Context Protocol servers

**Purpose:** Bridge AI models to your systems — databases, APIs, GitHub, custom tools.

**Put here:**

- One subfolder per MCP server (e.g. `database-mcp/`, `github-mcp/`)
- Tool definitions, resources, and server config

**When to use:** when an agent needs live access to data or actions your codebase alone cannot provide

→ See [`mcps/README.md`](./mcps/README.md)

### `workflows/` — automation and orchestration

**Purpose:** Connect systems without writing full apps — scheduled jobs, webhooks, notifications.

**Put here:**

- n8n workflow exports, Make/Zapier configs, or orchestration docs
- Flows that link `services/`, `data/pipelines/`, and `agents/`

**Examples:** new-order → Slack alert, nightly ETL trigger, lead → CRM sync

→ See [`workflows/README.md`](./workflows/README.md)

### `packages/` — shared libraries

**Purpose:** Versionable code reused by multiple apps, agents, or pipelines.

**Put here:**

- Shared TypeScript types (`packages/shared/` → `@repo/shared-types`)
- UI component libraries, API clients, analytics SDKs

**Rule:** if `uis/` and `services/` both need the same interface → extract it here

→ See [`packages/README.md`](./packages/README.md)

### `shared/` — loose shared assets

**Purpose:** Resources that are not a full package — schemas, templates, static assets, short docs.

**Put here:**

- JSON schemas, email templates, OpenAPI specs, design tokens
- Anything reused but too small or non-code for `packages/`

→ See [`shared/README.md`](./shared/README.md)

### `tests/` — cross-cutting tests

**Purpose:** Tests that do not belong to a single project, or that an assignment asks for at the root.

| Subfolder | Purpose | What you do here |
| --- | --- | --- |
| [`tests/pipelines/`](./tests/pipelines/README.md) | Unit tests for the pipelines in `data/pipelines/` | Test the tasks in isolation, with in-memory data; run them with the `data/pipelines` environment |

### `docs/` — cross-cutting documentation

**Purpose:** Architecture and decisions that span the whole company project.

**Put here:**

- System architecture diagrams, ADRs, security/observability guides
- Conventions not tied to one app or agent

→ See [`docs/README.md`](./docs/README.md)

### `infra/` — infrastructure and deployment

**Purpose:** How the company project runs in Docker, cloud, or CI.

**Put here:**

- Dockerfiles, Terraform, K8s manifests, Nginx configs, CI/CD pipelines

**Keep at repo root:** `docker-compose.yml` — orchestrates local dev for `services/`, databases, and other containers from one place.

→ See [`infra/README.md`](./infra/README.md)

### `scripts/` — helper scripts

**Purpose:** Small, repeatable automation — not full apps.

**Put here:**

- Setup scripts, seed data generators, lint wrappers, one-off migrations
- Document each script: what it does, args, and how to run it

**Difference from `internal/`:** scripts are usually single files; `internal/` tools are structured projects with their own deps and tests.

→ See [`scripts/README.md`](./scripts/README.md)

### `internal/` — internal developer tools

**Purpose:** Robust utilities for the engineering team.

**Put here:**

- CLIs, packaged migration tools, prompt evaluators
- Tools with their own `package.json`, tests, and install steps

→ See [`internal/README.md`](./internal/README.md)

---

## Where should I put this?

Quick decision guide:

```text
Does it have buttons and screens?          → uis/
Does it run on a server / API / queue?     → services/
Is it raw or transformed data?             → data/raw/ or data/process/
Does it move data between systems?         → data/pipelines/
Do you measure AI/pipeline quality?        → data/eval/
Is it a unit test for a pipeline?          → tests/pipelines/
Is it an AI assistant with a goal?         → agents/
Is it a reusable AI capability/instruction?→ skills/
Does AI need to call external tools/APIs?  → mcps/
Is it n8n / scheduled automation?          → workflows/
Will 2+ folders import the same code?      → packages/
Is it a schema/template/asset, not a lib?  → shared/
Is it architecture or team-wide docs?      → docs/
Is it docker-compose for local dev?        → repo root
Is it Docker / deploy / cloud config?      → infra/
Is it a one-off script?                    → scripts/
Is it a CLI tool with its own package?     → internal/
```

---

## Repository structure (tree)

```text
ai-engineering-company-project-monorepo/
├── README.md / README.es.md   # This guide
├── AGENTS.md                  # Instructions for coding agents (+ .agents/ rules and skills)
├── CONTEXT.md / CONTEXT.es.md # Brasaland company briefing
├── company-choice.md          # Company choice and personal focus
├── memory-bank/               # Project brief, tech context and progress
├── docker-compose.yml         # ← Local dev orchestration (repo root; not created yet)
├── uis/                       # Frontends (website, backoffice, dashboards)
├── services/                  # Centralized FastAPI company API
├── data/
│   ├── raw/                   # Source datasets
│   ├── pipelines/             # ETL/ELT jobs
│   ├── process/               # Clean / intermediate outputs
│   └── eval/                  # Evaluation sets and metrics
├── tests/pipelines/           # Unit tests for the pipelines
├── agents/                    # AI agents (+ _template/ starter)
├── skills/                    # Reusable agent skills
├── mcps/                      # MCP servers for tool access
├── workflows/                 # n8n and automation flows
├── packages/                  # Shared libraries (@repo/shared-types, …)
├── shared/                    # Schemas, templates, loose assets
├── docs/                      # Architecture and cross-cutting docs
├── infra/                     # Docker, Terraform, deployment
├── scripts/                   # Helper scripts
└── internal/                  # Internal CLIs and dev tools
```

---

## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

This template was built as part of the 4Geeks Academy AI Engineering Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) and [@alezanchezr](https://x.com/alesanchezr) and many other contributors. Find out more about our [AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering), and [other courses](https://4geeksacademy.com/en/program-comparison).

You can find other templates and resources like this at the [4Geeks Academy GitHub page](https://github.com/4geeksacademy).

_This template is maintained by 4Geeks Academy for the AI Engineering track. For exclusive use in the programme._
