# Brasaland API (`services/brasaland-api`)

Brasaland's central API, built with FastAPI and organized by domain as described in [`docs/ARCHITECTURE_PROPOSAL.md`](../../docs/ARCHITECTURE_PROPOSAL.md). It implements two domains:

- **`incidents`:** the analysis of the operational incidents CSV used by Operations and the backoffice.
- **`suppliers`:** Procurement's supplier directory, stored in TinyDB.

> _Spanish version: [README.es.md](./README.es.md)._

## Status

- **Implemented:** the `incidents` and `suppliers` domains, and `GET /health`.
- **Not built yet:** authentication and per-environment configuration, apart from `BRASALAND_DB_PATH`. Routes are not protected, so the service **must not be published** yet.
- **Storage:**
  - The latest incident analysis is kept in memory and is lost when the API restarts.
  - Suppliers are stored in a TinyDB file, `storage/brasaland-db.json`, which survives restarts. TinyDB is temporary until Postgres with an ORM exists. In both domains, only `repository.py` and `database.py` know about storage.

## Requirements

- Python 3.11 or later (tested with 3.12).
- [uv](https://docs.astral.sh/uv/) to install and run it. On Windows: `winget install --id astral-sh.uv -e`. After installing it, open a new terminal so the PATH includes it.

## Install and run

From this folder:

```bash
uv sync --extra dev                                 # creates .venv and installs what uv.lock pins
uv run seed                                         # loads the briefing suppliers (optional)
uv run uvicorn app.main:app --reload --port 8000
```

- Interactive docs: http://localhost:8000/docs
- API contract: http://localhost:8000/openapi.json

<details>
<summary>Without uv, with pip</summary>

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"     # on macOS or Linux: .venv/bin/python
.venv\Scripts\seed
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

pip does not use the versions pinned in `uv.lock`.
</details>

## Tests

```bash
uv run pytest -v
```

The 132 tests cover:

- **`incidents` (24):** file reading, the briefing values, the analysis JSON, the exported CSV, and every input error. The rules are also covered by the 32 tests of the console script (`scripts/incident-report/`), which uses the same service.
- **`suppliers` (108):**
  - the model, with the exact briefing fields and values, and every 422 rejection;
  - the seeder: that it does not duplicate and that it reports the count on the console;
  - the repository, including persistence and writes from two processes;
  - every endpoint with its HTTP codes.

Each test uses a temporary TinyDB database, so it never touches `storage/`.

## Structure

```
app/
├── main.py                 # Creates the app, GET /health, registers routers under /api/v1 and seeds on startup
├── core/errors.py          # Single error format
└── domains/
    ├── incidents/
    │   ├── router.py       # Endpoints: HTTP translation only
    │   ├── service.py      # Validation and analysis rules (standard library only)
    │   ├── exceptions.py   # Incident file errors
    │   ├── schemas.py      # Response format
    │   ├── repository.py   # Latest analysis, in memory
    │   └── dependencies.py # Repository injection
    └── suppliers/
        ├── models.py       # Pydantic models: Supplier, SupplierCreate, RateUpdate, StatusUpdate
        ├── database.py     # TinyDB initialization and file path
        ├── repository.py   # Reads and writes; the only piece that knows TinyDB
        ├── router.py       # /suppliers endpoints
        ├── seed.py         # Initial suppliers from the briefing (`uv run seed`)
        ├── exceptions.py   # DuplicateSupplierError
        └── dependencies.py # Repository injection
storage/                    # brasaland-db.json (TinyDB); ignored by Git
tests/                      # Mirrors the app/ structure
```

`incidents/service.py` is the **source of truth** for the incident rules. It only uses the standard library because the `scripts/incident-report/analyze.py` script imports it without installing anything.

## `incidents` domain

### `POST /api/v1/incidents/analyze`

Receives the CSV as `multipart/form-data` in the `file` field. It validates it, summarizes it and stores it as the latest analysis.

The response (200) includes:

- `source_file` and `analyzed_at`;
- `total_records`, `valid_records` and `invalid_records`;
- `invalid_breakdown`: all 7 rules, always, with their count;
- `invalid_records_detail`: ID, file row (the header is row 1) and rules of each invalid record;
- `categories` and `statuses`: code, count and percentage over valid records;
- `satisfaction`: closed cases, scored cases, average and the 1-to-5 distribution.

### `GET /api/v1/incidents/results/export`

Downloads the latest analysis as `results.csv`, with `Content-Disposition: attachment`. It has one row per metric, with the `metric`, `value` and `percentage` columns, the same as the script's export.

## `suppliers` domain

It is the single source of truth for Brasaland's supplier directory, replacing Procurement's spreadsheet.

### Model

Names and values match the briefing exactly:

| Field | Type | Rules |
|---|---|---|
| `name` | text, required | Not empty; unique, ignoring case and surrounding spaces |
| `country` | text, required | `"Colombia"` or `"USA"` |
| `categories` | list, required | At least 1, no repeats, from `carne`, `verduras_y_hortalizas`, `salsas_y_condimentos`, `bebidas`, `packaging`, `productos_limpieza`, `lacteos`, `carbon_y_combustible` |
| `rate_per_unit` | number, required | Greater than 0. Rejects text, booleans, NaN and infinity |
| `currency` | text, required | `"COP"` for Colombia and `"USD"` for USA |
| `status` | text, required | `"active"` or `"suspended"` |
| `contact_email` | text, optional | Valid email |
| `notes` | text, optional | Up to 1000 characters |
| `id` | integer, generated | `doc_id` assigned by TinyDB |
| `updated_at` | datetime, generated | UTC; set on creation and every time `rate_per_unit` changes |

Clients cannot send `id`, `updated_at` or any unknown field: the API responds 422.

### Endpoints

| Endpoint | Success | Errors |
|---|---|---|
| `POST /api/v1/suppliers` | 201 with the full supplier and its `id` | 422 if the input is invalid; 409 `duplicate_supplier` if the name already exists |
| `GET /api/v1/suppliers?country=&category=` | 200. Without parameters, all of them; filters can be combined | 422 if a filter has an unknown value |
| `GET /api/v1/suppliers/{id}` | 200 | 404 `supplier_not_found` |
| `PATCH /api/v1/suppliers/{id}/rate` | 200 with `{"rate_per_unit": ...}`. Updates `updated_at` | 404; 422 if the rate is ≤ 0 or missing |
| `PATCH /api/v1/suppliers/{id}/status` | 200 with `{"status": ...}`. Does not change `updated_at`, which is the date of the last rate change | 404; 422 if the status is invalid |
| `DELETE /api/v1/suppliers/{id}` | 200 with the deleted supplier | 404 |

According to the briefing, suppliers are not deleted: they are suspended. `DELETE` only exists to correct wrong data.

### Seeder and TinyDB file

- **`uv run seed`:** inserts the 15 briefing suppliers that do not exist yet, comparing by name. It ends with a message such as `Seeder completado: 15 proveedores insertados, 0 ya existían. Total en la base: 15 (...)`. Running it again does not duplicate anything.
- **On API startup:** it seeds only if the table is empty, so the demo never starts empty. A supplier deleted with `DELETE` does not come back on restart; `uv run seed` does restore it.
- **File:** `storage/brasaland-db.json`, readable UTF-8, ignored by Git. It can be changed with the `BRASALAND_DB_PATH` variable.
- **Back to the initial data:** delete the file and restart the API, or run `uv run seed`.
- **Two processes on the same file:** the repository uses no cache and computes each ID from the file, so `uv run seed` can run while the API is up. Even so, TinyDB is not designed for many processes writing at once. It is enough for a directory of about 20 suppliers managed by a small team.

## `GET /health`

Returns `{"status": "ok"}`. It is outside `/api/v1` and has no authentication.

## Errors

Every error responds with the format `{"error": {"code": "...", "message": "..."}}`. The `code` is stable so that a program can read it, and the `message` is in Spanish so it can be shown to the user. Validation errors add `details`, a list of `{"field", "message"}` that says which field failed and why.

| Case | HTTP | `code` |
|---|---|---|
| The `file` field was not sent | 400 | `missing_file` |
| The file has no `.csv` extension | 415 | `unsupported_file_type` |
| The file is empty | 400 | `empty_file` |
| It exceeds 5 MB | 413 | `file_too_large` |
| It is not UTF-8 | 422 | `invalid_encoding` |
| Missing columns; the message says which | 422 | `missing_columns` |
| It only has the header | 422 | `no_records` |
| Export with no previous analysis | 404 | `no_analysis` |
| Supplier does not exist | 404 | `supplier_not_found` |
| A supplier with that name already exists | 409 | `duplicate_supplier` |
| Malformed request or data that does not match the model | 422 | `invalid_request` (with `details`) |

The incident file type is validated by extension, not by `Content-Type`, because Windows sends CSV files as `application/vnd.ms-excel`.

422 example:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "La petición no es válida. Revisa: currency, status.",
    "details": [
      {"field": "currency", "message": "Un proveedor de USA debe usar USD."},
      {"field": "status", "message": "Debe ser uno de estos valores: 'active' o 'suspended'."}
    ]
  }
}
```

## Who uses it

- **`uis/backoffice`:** through its intermediary `app/api/[...path]/route.ts` (BFF pattern), with the server variable `API_BASE_URL=http://localhost:8000/api/v1`. The browser never calls the API directly, so no CORS is needed. The `/incidencias` and `/proveedores` tools use it.
- **`scripts/incident-report/analyze.py`:** imports `incidents/service.py` directly; it does not use HTTP.

## Differences from the course assignment

The assignments ask for `/services/api`, with routes such as `/api/incidents/...` or `/suppliers`, and loose files (`main.py`, `models.py`, `database.py`, `routes/suppliers.py`, `seed.py`). This service follows the architecture proposal: `services/brasaland-api/`, one folder per domain and `/api/v1/...`. It does so for two reasons:

- it is the agreed contract for the whole backend: one folder per service and a single API version (sections 2.2 and 3.1);
- a second service for each exercise would duplicate environments, ports and rules.

The assignment's file names are kept inside the `suppliers` domain. From the browser, routes look as in the assignment: the backoffice exposes `/api/suppliers` and `/api/incidents/...`, and its intermediary forwards them to `/api/v1/...`.

Every divergence from the briefings and assignments, with its reasons, is in [`docs/BRIEFING_DIVERGENCES.md`](../../docs/BRIEFING_DIVERGENCES.md).
