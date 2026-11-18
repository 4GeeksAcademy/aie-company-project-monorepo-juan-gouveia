# Brasaland API (`services/brasaland-api`)

Brasaland's central API, built with FastAPI and organized by domain as described in [`docs/ARCHITECTURE_PROPOSAL.md`](../../docs/ARCHITECTURE_PROPOSAL.md). It implements these domains:

- **`incidents`:** the analysis of the operational incidents CSV used by Operations and the backoffice, and the centralized incident manager (registration, tracking and metrics).
- **`suppliers`:** Procurement's supplier directory, stored in TinyDB.
- **`auth`, `users` and `profiles`:** JWT sign-in, users (credentials only) and profiles (name and contact details), stored in TinyDB (ticket AUTH-01).

> _Spanish version: [README.es.md](./README.es.md)._

## Status

- **Implemented:** the `incidents` and `suppliers` domains, authentication (`/auth`, `/users`, `/profiles`) and `GET /health`.
- **Passwords (AUTH-03, branch `feature/password-reset`):** reset by email (Resend) and change while signed in. See [Password reset and change](#password-reset-and-change).
- **Incident manager (branch `feature/incident-manager`):** creation, filtered list, detail, status changes and metrics. See [Centralized incident manager](#centralized-incident-manager).
- **Protected routes (AUTH-01):** every route requires a valid token except `POST /auth/login`, `POST /users` (sign-up), `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/reset-password/validate` (all three from AUTH-03) and `GET /health`. That includes the 7 `incidents` routes (2 from the analyzer and 5 from the manager) and the 6 `suppliers` routes, which are protected when their routers are registered in `main.py`. A test walks the OpenAPI schema and fails if a new route is accidentally left unprotected.
- **Storage:**
  - The latest incident analysis is kept in memory and is lost when the API restarts.
  - Suppliers and the manager's incidents are stored in a TinyDB file, `storage/brasaland-db.json`, which survives restarts. Each has its own table, and they share one lock per file. TinyDB is temporary until Postgres with an ORM exists.
  - Users, profiles and password reset links (`password_resets`) are stored in another TinyDB file, `storage/auth-db.json`. As the briefing requires, users and profiles will stay in TinyDB even after PostgreSQL arrives.
  - Inserts into that file compute the document ID by reading the file, so they do not clash with writes from another process (for example, `uv run create-admin` while the API is running).
  - In every domain, only `repository.py` and `database.py` know about storage.

## Requirements

- Python 3.11 or later (tested with 3.12).
- [uv](https://docs.astral.sh/uv/) to install and run it. On Windows: `winget install --id astral-sh.uv -e`. After installing it, open a new terminal so the PATH includes it.

## Install and run

From this folder:

```bash
uv sync --extra dev                                 # creates .venv and installs what uv.lock pins
cp .env.example .env                                # and fill in SECRET_KEY (see below)
uv run seed                                         # loads the briefing suppliers (optional)
uv run create-admin                                 # creates the first administrator (optional)
uv run --env-file .env uvicorn app.main:app --reload --port 8000
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

pip does not use the versions pinned in `uv.lock`, and `uvicorn` needs `--env-file .env` to load the configuration.
</details>

### Environment variables

The API **does not start** if `SECRET_KEY` or `ACCESS_TOKEN_EXPIRE_MINUTES` is missing or invalid: the error names the variable to check. They have no default value in the code. Locally they are read from the `.env` file (ignored by Git) with `uv run --env-file .env`. The template is [`.env.example`](./.env.example).

| Variable | Required | Use |
|---|---|---|
| `SECRET_KEY` | Yes | JWT signing key, at least 32 characters. Generate one with `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | Minutes an access token is valid (integer greater than 0) |
| `AUTH_DB_PATH` | No | TinyDB file for users and profiles; defaults to `storage/auth-db.json` |
| `BRASALAND_DB_PATH` | No | TinyDB file for suppliers; defaults to `storage/brasaland-db.json` |
| `RESEND_API_KEY` | No | [Resend](https://resend.com/api-keys) API key with "Sending access". **It is a secret: it only goes in `.env`.** Without it, the API starts, logs a warning and does not send password reset emails |
| `EMAIL_FROM` | No | Sender of the emails; defaults to `Brasaland <onboarding@resend.dev>`. Without a verified domain in Resend, that sender only delivers to the Resend account's email |
| `FRONTEND_URL` | No | Backoffice address, used for the `<FRONTEND_URL>/reset-password?token=...` link; defaults to `http://localhost:3001` |
| `PASSWORD_RESET_EXPIRE_MINUTES` | No | Minutes a reset link stays valid, between 15 and 60; defaults to 30. With a value outside that range, the API does not start |

## Tests

```bash
uv run pytest -v
```

The 539 tests cover:

- **`core` (62):** configuration from the environment (missing or invalid variables, the API not starting without a key), password hashing and tokens (expired, signed with another key, tampered with, unsigned or missing claims; access and reset tokens), email sending, and error headers.
- **Incident manager (71):** the exact briefing values and the lifecycle; every required field and every value that is not allowed, with 400 and its field; the filters; valid and rejected transitions; `/summary` with data and with an empty database; the 404; the generic 500 without internal details; seed loading without duplicates; and that suppliers and incidents share the file and its lock.
- **`incidents`, analyzer (24):** file reading, the briefing values, the analysis JSON, the exported CSV, and every input error. The rules are also covered by the 32 tests of the console script (`scripts/incident-report/`), which uses the same service.
- **`suppliers` (108):**
  - the model, with the exact briefing fields and values, and every 422 rejection;
  - the seeder: that it does not duplicate and that it reports the count on the console;
  - the repository, including persistence and writes from two processes;
  - every endpoint with its HTTP codes.
- **`users` (79), `profiles` (30) and `auth` (71):**
  - the briefing roles, the normalized email and the password limits;
  - that plain text never reaches the file and that `name`, `phone` and `address` only live in the profile;
  - the profile created with the user and deleted with it;
  - `uv run create-admin`;
  - sign-in with JSON and with a form, `get_current_user` (401 without a token, or with a malformed or expired one, or one for a deleted user; 403 if deactivated);
  - every endpoint, including the 403 when a user tries to read, change or delete someone else's account or profile (an admin can read any profile, but not change it);
  - password reset and change (AUTH-03).
- **Protected routes (94):** the 13 `incidents` (analyzer and manager) and `suppliers` routes respond 401 without a token, or with a malformed, unsigned, expired or foreign-key token, and work as before with a valid token. `/health` stays public, and no route is open other than the declared public ones. The existing `incidents` and `suppliers` tests send the token of a test user.

Each test uses temporary TinyDB databases and its own configuration, so it never touches `storage/` or depends on `.env`.

## Structure

```
app/
├── main.py                 # Creates the app, GET /health, registers routers under /api/v1, validates configuration and seeds on startup
├── core/
│   ├── config.py           # Environment variables (JWT, email and password reset) and API_PREFIX
│   ├── security.py         # bcrypt hashing and JWTs: access tokens and reset tokens (purpose, jti)
│   ├── email.py            # EmailMessage and senders: Resend, or disabled without RESEND_API_KEY
│   ├── storage.py          # Shared brasaland-db.json: path, opening, per-file lock and insert_with_file_id
│   └── errors.py           # Single error format
└── domains/
    ├── auth/
    │   ├── router.py       # Login, /auth/me and forgot/reset/change-password
    │   ├── dependencies.py # get_current_user, require_admin and the "your own account or admin" rule
    │   ├── schemas.py      # LoginRequest, Token, CurrentUser and password inputs
    │   ├── passwords.py    # Password reset and change; hourly limit
    │   ├── emails.py       # Password reset email (HTML and text)
    │   ├── models.py       # PasswordReset
    │   └── repository.py   # password_resets table
    ├── users/
    │   ├── models.py       # Role, User, UserCreate, UserUpdate, UserPublic
    │   ├── database.py     # TinyDB for users and profiles (auth-db.json) with a shared lock
    │   ├── repository.py   # User reads and writes
    │   ├── service.py      # Create, get by ID or email, update, delete and authenticate
    │   ├── router.py       # /users endpoints
    │   ├── create_admin.py # `uv run create-admin`
    │   ├── exceptions.py   # DuplicateEmailError
    │   └── dependencies.py # Storage injection
    ├── profiles/
    │   ├── models.py       # Profile, ProfileUpdate
    │   ├── repository.py   # Profile reads and writes
    │   └── router.py       # GET and PUT /profiles/me and /profiles/{user_id}
    ├── incidents/
    │   ├── router.py       # CSV analyzer: endpoints, HTTP translation only
    │   ├── service.py      # Re-exports the CSV rules from packages/shared (brasaland_shared)
    │   ├── exceptions.py   # File errors (from packages/shared) and invalid transition
    │   ├── schemas.py      # Analysis response format
    │   ├── repository.py   # Latest analysis, in memory
    │   ├── models.py       # Manager: Incident, briefing enumerations and lifecycle
    │   ├── incident_repository.py # Manager: incidents and incident_seed_log tables (TinyDB)
    │   ├── manager_router.py # Manager: /incidents endpoints
    │   └── dependencies.py # Repository injection
    └── suppliers/
        ├── models.py       # Pydantic models: Supplier, SupplierCreate, RateUpdate, StatusUpdate
        ├── database.py     # Suppliers table; path and opening come from core/storage.py
        ├── repository.py   # Reads and writes; the only piece that knows TinyDB
        ├── router.py       # /suppliers endpoints
        ├── seed.py         # Initial suppliers from the briefing (`uv run seed`)
        ├── exceptions.py   # DuplicateSupplierError
        └── dependencies.py # Repository injection
storage/                    # brasaland-db.json and auth-db.json (TinyDB); ignored by Git
tests/                      # Mirrors the app/ structure
```

The incidents CSV rules live in the shared package [`packages/shared`](../../packages/shared/README.md) (`brasaland_shared.incidents`), which `scripts/incident-report/analyze.py` and `scripts/seed_incidents.py` also use. The API installs it as a local dependency (`[tool.uv.sources]` in `pyproject.toml`), so `uv sync` is enough; `incidents/service.py` only re-exports what the analyzer uses.

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

## Centralized incident manager

Incident registration and tracking from the backoffice (branch `feature/incident-manager`). It shares the `/incidents` prefix with the CSV analyzer, but they are separate pieces: the analyzer does not store incidents.

### Model

`Incident` uses exactly the briefing's names and values:

| Field | Values |
|---|---|
| `id` | Integer generated by TinyDB |
| `title` | Required, 1 to 120 characters |
| `description` | Required, 1 to 2,000 characters |
| `category` | `equipment_failure`, `supply_issue`, `customer_complaint`, `staff_issue`, `facility_issue`, `pos_system`, `delivery_issue`, `other` |
| `status` | `open`, `in_progress`, `resolved`, `discarded` |
| `origin` | `customer`, `branch`, `internal` |
| `branch` | Required for every origin: `central` and the briefing's 14 locations (`medellin_centro` … `fort_lauderdale`) |
| `created_at`, `updated_at` | Date and time in UTC, generated by the system |

- Every new incident starts as `open`: `POST` accepts `status` only with that value.
- Lifecycle: `open → in_progress | discarded`; `in_progress → resolved | discarded`. `resolved` and `discarded` are final.
- It is stored in the `incidents` table of `storage/brasaland-db.json`, the same file as suppliers and with the same lock (`core/storage.lock_for`), because TinyDB rewrites the whole file on every write.

### Endpoints

| Method and route | Response | Errors |
|---|---|---|
| `POST /api/v1/incidents` | 201 with the incident | 400 `invalid_request` (with `details`) |
| `GET /api/v1/incidents` | 200 with the list, newest first. Optional `status`, `origin`, `branch` and `category` filters, which can be combined | 400 if a filter is not valid |
| `GET /api/v1/incidents/summary` | 200 with `total`, `by_status`, `by_category`, `by_origin` and `by_branch`; each breakdown includes every value, also at 0 | — |
| `GET /api/v1/incidents/{id}` | 200 with the incident | 404 `incident_not_found` |
| `PATCH /api/v1/incidents/{id}/status` | 200 with the incident; only changes `status` and `updated_at` | 400 `invalid_transition` (the message says which states are allowed) or `invalid_request`; 404 |

- **Validation errors with 400:** on these routes, as their assignment requires, a missing field or a value that is not allowed returns 400, with the same body as the 422 in the rest of the API. The other routes still return 422.
- **Empty database:** the list is `[]` and the metrics are 0.

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

## Authentication: `auth`, `users` and `profiles`

No route that exposes or changes sensitive data may respond without a valid session (ticket AUTH-01). The API is **stateless**: there are no server sessions and no cookies. Sign-in returns a JWT, and every protected request sends it in the `Authorization: Bearer <token>` header.

### Models

- **`User`** stores credentials only: `id` (UUID4), `email` (unique, lowercase), `hashed_password` (bcrypt), `is_active`, `role` and `created_at`. The hash never appears in a response.
- **`role`** only accepts `admin`, `manager` or `user`. Sign-up always creates `user`.
- **`Profile`** stores the display name and contact details: `id`, `user_id`, `name`, `phone` and `address`. It is created with the user and deleted with them.
- **Password:** from 8 characters to 72 bytes (the bcrypt limit). It is hashed with libpass (`from passlib.hash import bcrypt`); plain text is never stored or compared.
- **Other modules** reference a user by their `id`, under the name `user_uuid`. Users and profiles are not copied to other databases.

### Token

- Signed with HS256 (`python-jose`) using `SECRET_KEY`. It expires after `ACCESS_TOKEN_EXPIRE_MINUTES` minutes.
- It only carries `sub` (the user's `id`), `iat` and `exp`. The role is read from the database on every request, so a role change or a deactivation applies without waiting for the token to expire.

### Endpoints

| Endpoint | Access | Success | Errors |
|---|---|---|---|
| `POST /api/v1/auth/login` | Public | 200 `{access_token, token_type: "bearer"}` | 401 `invalid_credentials`, 403 `inactive_user`, 415, 422 |
| `GET /api/v1/auth/me` | Token | 200 with `id`, `email`, `role` and `profile` | 401, 403 |
| `POST /api/v1/users` | Public (sign-up) | 201 with the user and their profile | 409 `duplicate_email`, 422 (also if `role` is sent) |
| `GET /api/v1/users` | Admin only | 200 with the list | 401, 403 |
| `GET /api/v1/users/{id}` | Own account or admin | 200 | 401, 403, 404 `user_not_found` |
| `PUT /api/v1/users/{id}` | Own account or admin. `role` and `is_active`, admin only | 200 | 401, 403, 404, 409, 422 |
| `DELETE /api/v1/users/{id}` | Own account or admin | 200 with the deleted user (also deletes their profile) | 401, 403, 404 |
| `GET /api/v1/profiles/me` | Token | 200 | 401, 404 `profile_not_found` |
| `PUT /api/v1/profiles/me` | Token (own profile only) | 200 | 401, 404, 422 |
| `GET /api/v1/profiles/{user_id}` | Own profile or admin | 200 | 401, 403 `forbidden`, 404 (admin only) |
| `PUT /api/v1/profiles/{user_id}` | Profile owner only, even for an admin | 200 | 401, 403 `forbidden`, 404, 422 |

- **Sign-in:** accepts JSON `{"email", "password"}` and also the `username`/`password` form sent by the **Authorize** button in `/docs` (`username` is the email). If the email does not exist or the password is wrong, the response is the same, and bcrypt runs in both cases so that response times do not reveal which emails are registered.
- **`PUT`:** changes only the fields sent. In profiles, `null` clears a field.
- **403 between users:** a non-admin user gets 403 when accessing another account, whether or not that ID exists, so that existing IDs are not revealed.
- **First administrator:** `uv run create-admin` asks for the email and the password (without showing it) and creates the admin. If the email already exists, it makes that user an admin and reactivates them without changing their password. After that, an admin changes roles with `PUT /users/{id}`.

### Password reset and change

Ticket AUTH-03. Emails are sent with [Resend](https://resend.com), chosen over SendGrid because its free plan does not expire and it lets you complete the flow without your own domain. The full reasons are in `docs/BRIEFING_DIVERGENCES.md`.

| Endpoint | Access | Success | Errors |
|---|---|---|---|
| `POST /api/v1/auth/forgot-password` | Public | Always 200, with the same message | 422 if the email is not valid |
| `POST /api/v1/auth/reset-password/validate` | Public | 200 if the link works (it is not consumed) | 400 `invalid_reset_token`, `reset_token_expired` or `reset_token_used`; 422 |
| `POST /api/v1/auth/reset-password` | Public | 200 | 400 (same codes); 422 if the new password breaks the rules |
| `POST /api/v1/auth/change-password` | Token | 200 with a new access token | 400 `invalid_current_password`, 401, 422 |

- **`forgot-password`** takes `{email}`. If the email belongs to an active account, it creates a `<FRONTEND_URL>/reset-password?token=...` link and sends it **after responding** (`BackgroundTasks`). That way the response, and its timing, are the same whether or not the account exists. If the provider fails, it only goes to the log, without recipient or link. At most **3 links per account per hour** are sent; the rest are silently ignored.
- **Link token:** a JWT signed with `SECRET_KEY`, with `sub`, `jti`, `iat`, `exp` and `purpose: "password_reset"`. It expires after `PASSWORD_RESET_EXPIRE_MINUTES` minutes. Its `jti` has a row in `password_resets`: once used, it is marked and stops working. Using a link also voids the user's other pending links. A reset token does not work as a session, and a session token does not work as a reset token.
- **Inputs:** `reset-password` takes `{token, new_password}` and `change-password` takes `{current_password, new_password}`. The new password follows the same rules as sign-up.
- **Sessions:** resetting or changing the password stores `password_changed_at`, and access tokens issued before it get 401 `session_revoked`. `change-password` returns a new token to stay in the current session and voids pending reset links. `iat` is in seconds, so a token issued in the same second as the change remains valid.
- **Email:** HTML with inline styles, a single column of at most 600 px and a large button (readable on mobile), plus a plain-text version.
- **Trying it without your own domain:** register a user with your Resend account's email, add `RESEND_API_KEY` to `.env` and call `forgot-password` with that email.

### Try it in `/docs`

1. `POST /api/v1/users` with `{"email": "...", "password": "..."}`.
2. **Authorize** button: type the email in `username`, and the password. You can also call `POST /api/v1/auth/login` and copy the `access_token`.
3. Call `GET /api/v1/auth/me`: it responds with your email, role and profile. Without a token it responds 401.

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
| Malformed CSV (e.g. an unclosed quote); the message gives the line | 422 | `malformed_csv` |
| It only has the header | 422 | `no_records` |
| Export with no previous analysis | 404 | `no_analysis` |
| Supplier does not exist | 404 | `supplier_not_found` |
| A supplier with that name already exists | 409 | `duplicate_supplier` |
| The access token is missing | 401 | `not_authenticated` |
| Malformed token, signed with another key, or for a deleted user | 401 | `invalid_token` |
| Expired token | 401 | `token_expired` |
| Token issued before the last password change | 401 | `session_revoked` |
| Password reset link not valid, expired or already used | 400 | `invalid_reset_token`, `reset_token_expired`, `reset_token_used` |
| Wrong current password in `change-password` | 400 | `invalid_current_password` |
| Wrong email or password at sign-in | 401 | `invalid_credentials` |
| Deactivated account | 403 | `inactive_user` |
| Access to another account, or an admin-only operation | 403 | `forbidden` |
| User does not exist (only an admin sees this) | 404 | `user_not_found` |
| The account has no profile | 404 | `profile_not_found` |
| A user with that email already exists | 409 | `duplicate_email` |
| Sign-in body is neither JSON nor a form | 415 | `unsupported_media_type` |
| Incident does not exist | 404 | `incident_not_found` |
| Status change the lifecycle does not allow | 400 | `invalid_transition` |
| Malformed request or data that does not match the model | 422 (400 in the incident manager) | `invalid_request` (with `details`) |
| Unexpected server error | 500 | `internal_error`, with a generic message; the details only go to the log |

401 responses include the `WWW-Authenticate: Bearer` header.

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

### Console commands

`uv run seed` and `uv run create-admin` write the result to `stdout` and errors to `stderr`, without a traceback, and exit with code 0 on success and 1 on failure (`create-admin` exits with 130 when cancelled with Ctrl+C). They detect a database that cannot be opened, is not valid JSON (it is left untouched) or cannot be written.

Both show the absolute path of the database they use, on purpose: only the person operating the server sees it, in their own console, and since `BRASALAND_DB_PATH` and `AUTH_DB_PATH` can point anywhere, it is how they confirm which file was changed. The API never returns that path to a client.

## Who uses it

- **`uis/backoffice`:** through its intermediary `app/api/[...path]/route.ts` (BFF pattern), with the server variable `API_BASE_URL=http://localhost:8000/api/v1`. The browser never calls the API directly, so no CORS is needed. The `/incidencias` and `/proveedores` tools use it, and so do the session views (`/login`, `/register`). The browser stores the token in `localStorage` and sends it in `Authorization: Bearer`; the intermediary forwards it as is (ticket AUTH-02).
- **`scripts/incident-report/analyze.py`:** uses the same rules as the API, from `packages/shared`; it does not use HTTP.
- **`scripts/seed_incidents.py`:** loads the historical CSV into the incident manager through the API repository (`IncidentRepository`) on the same TinyDB file; it does not use HTTP.

## Differences from the course assignment

The assignments ask for `/services/api`, with routes such as `/api/incidents/...` or `/suppliers`, and loose files (`main.py`, `models.py`, `database.py`, `routes/suppliers.py`, `seed.py`). This service follows the architecture proposal: `services/brasaland-api/`, one folder per domain and `/api/v1/...`. It does so for two reasons:

- it is the agreed contract for the whole backend: one folder per service and a single API version (sections 2.2 and 3.1);
- a second service for each exercise would duplicate environments, ports and rules.

Authentication follows the same pattern: the briefing asks for `/auth`, `/users` and `/profiles`, and here they live under `/api/v1`. Sign-in also accepts a form as well as JSON, and sign-up does not accept `role`.

The assignment's file names are kept inside the `suppliers` domain. From the browser, routes look as in the assignment: the backoffice exposes `/api/suppliers` and `/api/incidents/...`, and its intermediary forwards them to `/api/v1/...`.

Every divergence from the briefings and assignments, with its reasons, is in [`docs/BRIEFING_DIVERGENCES.md`](../../docs/BRIEFING_DIVERGENCES.md).
