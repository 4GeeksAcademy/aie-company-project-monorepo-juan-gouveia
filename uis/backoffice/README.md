# Brasaland backoffice

Internal application where Brasaland staff access their tools from a single place.

It addresses the needs in `CONTEXT.md` for modern internal systems. Its first tools support People and Culture recruiting and the review of business logic.

> _Spanish version: [README.es.md](./README.es.md)._

## Stack

Next.js 16 (App Router), React 19, TypeScript, and Tailwind CSS 4. It is an independent project: it shares no layout with `uis/website`.

## How to run it

Copy `.env.example` as `.env.local` and set the API URLs:

```bash
NEXT_PUBLIC_API_BASE_URL=<api-base-url>           # Tracker API
API_BASE_URL=http://localhost:8000/api/v1         # Brasaland API (services/brasaland-api)
```

Tools that use the Brasaland API need it to be running; see [`services/brasaland-api/README.md`](../../services/brasaland-api/README.md).

Then run:

```bash
npm install
npm run dev     # http://localhost:3001
npm run lint
npm run build
```

`npm install` links `@repo/brasa-core` from `packages/brasa-core`, so run it again after a fresh clone.

## Tools

| Route | Tool | Data |
|---|---|---|
| `/` | Home page with a card for each tool | `lib/tools.ts` |
| `/talento` | Talent Pipeline Tracker: candidates, status, stage, and notes | REST API |
| `/incidencias` | Incident analysis: uploads the Operations CSV, shows the summary and the invalid records with their reason, and downloads `results.csv` | Brasaland API, through the intermediary |
| `/proveedores` | Supplier directory: list of active and suspended suppliers, country and category filters, registration, rate updates and activating or suspending | Brasaland API (`suppliers` domain, TinyDB), through the intermediary |
| `/funciones` | Manual tests for filters, search, reports, and validations | `@repo/brasa-core` sample data |

## Adding a tool

1. Create its route in `app/<tool>/`.
2. Put its own files in `components/<tool>/` and `lib/<tool>/`. Reusable pieces stay directly in `components/`.
3. Add an entry to `lib/tools.ts`. The home page and navigation are generated from that list.

Internal areas, including training, join this project as tools, not as separate applications. Once authentication exists, each `lib/tools.ts` entry will declare the permission it needs, and the list will be filtered with `GET /auth/me`. That filter only affects the interface: real authorization lives in the API.

## Structure

- `app/`: root layout, home page, and one folder per tool.
- `app/api/[...path]/route.ts`: intermediary (BFF) to the Brasaland API. It forwards `GET`, `POST`, `PATCH` and `DELETE` on `/api/<path>` to `API_BASE_URL/<path>` with no logic, so the API URL stays on the server and CORS is not needed. If the variable is missing it returns 500 (`api_not_configured`); if the API does not respond, 502 (`api_unavailable`).
- `components/`: reusable base components, plus `talento/`, `funciones/`, `incidencias/`, and `proveedores/`. `FileDropzone` works for any tool that receives files.
- `hooks/`: custom hooks.
- `lib/`: `tools.ts`, `format.ts`, and one folder per tool.
- `types/`: API types.

## Known limitations

- **No authentication:** do not publish it until login exists.
- **`/incidencias` and `/proveedores` get 401 for now:** the Brasaland API requires a JWT on those routes (ticket AUTH-01), and the intermediary does not send it yet. This is expected: the frontend will be updated to send the token in a later phase.
- **`/funciones` is temporary:** it tests the rules in `@repo/brasa-core`, a transitional package. Once those rules move to the backend, it must be retired or call the API. Do not add business calculations to the frontends.
- **`/incidencias` downloads the API's latest analysis:** it is kept in memory, so if the API restarts the file must be uploaded again, and if two people analyze at the same time, the most recent one is downloaded.
- **`/proveedores` writes to the API's local database:** registrations and rate or status changes are saved in `services/brasaland-api/storage/brasaland-db.json`. To go back to the initial data, delete that file and restart the API. The interface does not offer deleting suppliers: the usual flow is to suspend them.
- **Header height:** `FilterBar` depends on the fixed header height (57 px on mobile and 89 px from `md`). Tool links are hidden on mobile, where staff navigate from the home page.
- **Shared API:** the tracker uses a shared playground API, so avoid test writes against it.
