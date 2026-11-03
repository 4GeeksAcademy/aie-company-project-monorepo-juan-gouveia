# Brasaland API (`services/brasaland-api`)

Brasaland's central API, built with FastAPI and organized by domain as described in [`docs/ARCHITECTURE_PROPOSAL.md`](../../docs/ARCHITECTURE_PROPOSAL.md). It currently implements the first domain, `incidents`: the analysis of the operational incidents CSV used by Operations and the backoffice.

> _Spanish version: [README.es.md](./README.es.md)._

## Status

- **Implemented:** the `incidents` domain and `GET /health`.
- **Not built yet:** database, authentication and per-environment configuration. Routes are not protected, so the service **must not be published** yet.
- **The latest analysis is kept in memory** and is lost when the API restarts. Once there is a database, only `repository.py` changes.

## Requirements

Python 3.11 or later (tested with 3.12).

## Install and run

From this folder, on Windows:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

On macOS or Linux, replace `.venv\Scripts\python` with `.venv/bin/python`.

- Interactive docs: http://localhost:8000/docs
- API contract: http://localhost:8000/openapi.json

## Tests

```bash
.venv\Scripts\python -m pytest -v
```

The 24 tests cover:

- file reading and the briefing values;
- the analysis JSON and the exported CSV;
- every input error.

The validation rules are also tested by the 32 tests of the console script (`scripts/incident-report/`), which uses the same service.

## Structure

```
app/
├── main.py                 # Creates the app, GET /health, and mounts routers under /api/v1
├── core/errors.py          # Single error format
└── domains/incidents/
    ├── router.py           # Endpoints: HTTP translation only
    ├── service.py          # Validation and analysis rules (standard library only)
    ├── exceptions.py       # Incident file errors
    ├── schemas.py          # Response format
    ├── repository.py       # Latest analysis, in memory
    └── dependencies.py     # Repository injection
tests/                      # Mirrors app/
```

`service.py` is the **source of truth** for incident rules. It only uses the standard library because `scripts/incident-report/analyze.py` imports it with nothing installed.

## Endpoints

### `POST /api/v1/incidents/analyze`

Receives the CSV as `multipart/form-data` in the `file` field. It validates and summarizes the file, and stores it as the latest analysis.

The response (200) includes:

- `source_file` and `analyzed_at`;
- `total_records`, `valid_records` and `invalid_records`;
- `invalid_breakdown`: all 7 rules, always, with their count;
- `invalid_records_detail`: the ID, file row (the header is row 1) and rules of each invalid record;
- `categories` and `statuses`: code, count and percentage of valid records;
- `satisfaction`: closed cases, scored cases, average and the 1–5 distribution.

### `GET /api/v1/incidents/results/export`

Downloads the latest analysis as `results.csv`, with `Content-Disposition: attachment`. There is one row per metric, with the columns `metric`, `value` and `percentage`, the same as the script's export.

### `GET /health`

Returns `{"status": "ok"}`. It is outside `/api/v1` and has no authentication.

## Errors

Every error uses the format `{"error": {"code": "...", "message": "..."}}`. The `code` is stable for programs to read, and the `message` is in Spanish so it can be shown to users.

| Case | HTTP | `code` |
|---|---|---|
| No `file` field was sent | 400 | `missing_file` |
| The file does not have a `.csv` extension | 415 | `unsupported_file_type` |
| The file is empty | 400 | `empty_file` |
| Larger than 5 MB | 413 | `file_too_large` |
| Not UTF-8 | 422 | `invalid_encoding` |
| Missing columns; the message lists them | 422 | `missing_columns` |
| Header only | 422 | `no_records` |
| Export with no prior analysis | 404 | `no_analysis` |
| Malformed request | 422 | `invalid_request` |

The file type is checked by extension, not by `Content-Type`, because Windows sends CSV files as `application/vnd.ms-excel`.

## Clients

- **`uis/backoffice`:** through its `app/api/[...path]/route.ts` intermediary (BFF pattern), with the server variable `API_BASE_URL=http://localhost:8000/api/v1`. The browser never calls the API directly, so CORS is not needed.
- **`scripts/incident-report/analyze.py`:** imports `service.py` directly, without HTTP.

## Differences from the course assignment

The assignment asks for `/services/api` and the routes `/api/incidents/...`. This service follows the architecture proposal (`services/brasaland-api/` and `/api/v1/...`) for two reasons:

- it is the agreed contract for the whole backend: one folder per service and a single API version (sections 2.2 and 3.1);
- departing from it in the first implemented domain would break that consistency.

From the browser, the routes look the same as in the assignment: the backoffice exposes `/api/incidents/...` and its intermediary forwards them to `/api/v1/incidents/...`.
