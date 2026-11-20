# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

## Services

| Service | What it does |
|---|---|
| [`brasaland-api/`](./brasaland-api/README.md) | Brasaland's central API (FastAPI), organized by domain. It implements the `incidents` domain (incident CSV analysis and results export), the `suppliers` domain (supplier directory in TinyDB) and the `inventory` domain (ingredient inventory in Supabase with SQLModel), plus JWT authentication (`auth`, `users` and `profiles`, in TinyDB). |
| [`telemetry/`](./telemetry/README.md) | Analysis pipeline for the telemetry technical report (`analysis.py`, with Pandas): daily operational metrics over `telemetry_events`. It is a Python package (`brasaland-telemetry`) that the API installs in editable mode; it is not a service that runs on its own. |

## Docker

The API runs in the `api` container: [`Dockerfile`](./Dockerfile) (Python 3.12 slim, `uv pip install -r requirements.txt` and Uvicorn with `--reload`). [`requirements.txt`](./requirements.txt) is generated from `brasaland-api/uv.lock`; its header explains how to regenerate it. Start it from the repository root with `docker compose up`; see [Running with Docker](../README.md#running-with-docker).

> _Spanish version: [README.es.md](./README.es.md)._
