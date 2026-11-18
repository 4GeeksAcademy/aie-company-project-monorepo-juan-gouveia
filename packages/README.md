# `packages` folder

This folder contains **shared packages** for the monorepo: internal libraries, utilities, types, shared components, SDKs, clients, and any code reused by multiple applications, agents, or pipelines.

Each subfolder under `packages/` should represent **one versionable package** (for example `shared-types`, `ui`, `analytics-sdk`) with its own README.

- **Main purpose**: encourage reuse and consistency across all company deliverables.
- **Recommendation**: document packages as you add them—their public API and how they are consumed from `uis/`, `services/`, `agents/`, and `workflows/`.

## Available packages

| Package | Folder | Purpose | Consumed by |
|---|---|---|---|
| [`@repo/brasa-core`](./brasa-core/README.md) | `brasa-core/` | Transitional: Brasaland domain models and business utilities, to be replaced by the backend | `uis/backoffice` |
| [`brasaland-shared`](./shared/README.md) (Python) and `@repo/shared-types` (TypeScript) | `shared/` | Incidents CSV rules shared by scripts and the API; base types (`Id`, `BaseEntity`) | `scripts/incident-report`, `scripts/seed_incidents.py` and `services/brasaland-api`; the types, not consumed yet |

> _Spanish version: [README.es.md](./README.es.md)._
