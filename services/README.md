# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

## Services

| Service | What it does |
|---|---|
| [`brasaland-api/`](./brasaland-api/README.md) | Brasaland's central API (FastAPI), organized by domain. It implements the `incidents` domain: incident CSV analysis and results export. |

> _Spanish version: [README.es.md](./README.es.md)._
