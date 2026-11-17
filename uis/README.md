# `uis` folder

This folder contains **all projects with a user interface** for the cross-functional AI Engineering company project — for example: a public website, admin dashboard frontend, ecommerce UI, customer portals, Streamlit/Gradio app or other frontend-only tools.

The two main projects stored here are:

- **`website`** — the company's public-facing web presence.
- **`backoffice`** — the internal admin application. This is the ideal place to develop multiple solutions within a single project: authentication, people management, operations management, internal communication, and other back-office capabilities.

Organize `uis/` by **different concerns** — each subfolder covers a distinct area of the company (for example, public web vs internal operations) and includes its own technical and functional documentation.

- **Main purpose**: to centralize in a single place all frontend applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them.

## Applications

| Application | Objective | Technology | Development port |
|---|---|---|---|
| [`website`](./website/README.md) | Landing page and Brasa Points registration for customers | Next.js, React, Tailwind CSS | 3000 |
| [`backoffice`](./backoffice/README.md) | Internal tools: Talent Pipeline Tracker and function tests | Next.js, React, Tailwind CSS | 3001 |

## Docker

Both apps run in a single `uis` container: [`Dockerfile`](./Dockerfile) (Node 22 Alpine, `npm ci` per app) and [`start.sh`](./start.sh), which starts `website` on 3000 and `backoffice` on 3001 with `next dev --webpack`. Start it from the repository root with `docker compose up`; see [Running with Docker](../README.md#running-with-docker).

> _Estas instrucciones también están disponibles en [español](./README.es.md)._
