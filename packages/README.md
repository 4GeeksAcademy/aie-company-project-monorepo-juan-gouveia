# `packages` folder

This folder contains **shared packages** for the monorepo: internal libraries, utilities, types, shared components, SDKs, clients, and any code reused by multiple applications, agents, or pipelines.

Each subfolder under `packages/` should represent **one versionable package** (for example `shared-types`, `ui`, `analytics-sdk`) with its own README.

- **Main purpose**: encourage reuse and consistency across all company deliverables.
- **Recommendation**: document packages as you add them—their public API and how they are consumed from `uis/`, `services/`, `agents/`, and `workflows/`.

## Available packages

| Package | Folder | Purpose | Consumed by |
|---|---|---|---|
| [`@repo/brasa-core`](./brasa-core/README.md) | `brasa-core/` | Transitional: Brasaland domain models and business utilities, to be replaced by the backend | `uis/backoffice` |
| `@repo/shared-types` | `shared/` | Base types (`Id`, `BaseEntity`) | Not consumed yet |

> _Spanish version: [README.es.md](./README.es.md)._
