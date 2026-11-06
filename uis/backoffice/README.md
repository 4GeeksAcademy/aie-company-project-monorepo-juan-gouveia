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

## Session

Every view requires a session except `/login` and `/register` (ticket AUTH-02). The public website (`uis/website`) is not affected.

| Route | View |
|---|---|
| `/login` | Email and password (with a button to show it). Stores the token and returns to the `?next=` route (internal routes only), or to `/`. Shows a notice if the session expired (`?reason=expired`) or the account is deactivated (`?reason=inactive`) |
| `/register` | Email, password (with a button to show it) and an optional profile (full name, phone and address). Calls `POST /users` and then `POST /auth/login`. API errors are shown next to each field |
| `/account/profile` | Requires a session. Shows the email and profile (from `GET /auth/me`) and lets the user edit full name, phone and address with `PUT /profiles/me`. Only changed fields are sent; an empty field is cleared. Saving updates the name in the header |

How it works:

- **Token:** stored in `localStorage` (`lib/auth/token.ts`). The shared client `lib/api-client.ts` sends it as `Authorization: Bearer <token>` to the intermediary, which forwards it to the API.
- **Protection:** protected views live in the `app/(protegido)/` route group, and any page created there is protected. Its layout uses `SessionProvider`, a client-side guard:
  - without a token, it redirects to `/login?next=<route>`;
  - with a token, it checks the session with `GET /auth/me` and shows nothing until it has it.

  `proxy.ts` is not used, because the server cannot read `localStorage`. `useSession()` gives access to the user, `refresh` and `logout`.
- **Session end:** on a 401, or a 403 `inactive_user`, the shared client deletes the token and redirects to the login with the reason. "Cerrar sesión" (in the header) deletes the token and goes to `/login`.
- **Several tabs:** if the token disappears in another tab, this one redirects to the login; if it changes, it reloads the user.

## Tools

| Route | Tool | Data |
|---|---|---|
| `/` | Home page with a card for each tool | `lib/tools.ts` |
| `/talento` | Talent Pipeline Tracker: candidates, status, stage, and notes | REST API |
| `/incidencias` | Incident analysis: uploads the Operations CSV, shows the summary and the invalid records with their reason, and downloads `results.csv` | Brasaland API, through the intermediary |
| `/proveedores` | Supplier directory: list of active and suspended suppliers, country and category filters, registration, rate updates and activating or suspending | Brasaland API (`suppliers` domain, TinyDB), through the intermediary |
| `/funciones` | Manual tests for filters, search, reports, and validations | `@repo/brasa-core` sample data |

## Adding a tool

1. Create its route in `app/(protegido)/<tool>/`, so it requires a session. The group does not change the URL.
2. Put its own files in `components/<tool>/` and `lib/<tool>/`. Reusable pieces stay directly in `components/`.
3. Add an entry to `lib/tools.ts`. The home page and navigation are generated from that list.

Internal areas, including training, join this project as tools, not as separate applications. Later on, each `lib/tools.ts` entry may declare the permission it needs, and the list will be filtered with `GET /auth/me`. That filter will only affect the interface: real authorization lives in the API.

Calls to the Brasaland API go through `apiJson` or `apiFetch` in `lib/api-client.ts`, which add the token, turn errors into an `ApiError` (`status`, `code`, `message`, per-field `details`) and end the session on a 401.

## Structure

- `app/`: root layout (no header) and two route groups:
  - `(protegido)/`: home page and one folder per tool, with the session guard;
  - `(publico)/`: `login/` and `register/`, with a header without navigation.
- `app/api/[...path]/route.ts`: intermediary (BFF) to the Brasaland API.
  - It forwards `GET`, `POST`, `PUT`, `PATCH` and `DELETE` on `/api/<path>` to `API_BASE_URL/<path>`, with the `Content-Type`, `Accept` and `Authorization` headers, applying no logic.
  - The API URL stays on the server and CORS is not needed.
  - If the variable is missing it returns 500 (`api_not_configured`); if the API does not respond, 502 (`api_unavailable`).
- `components/`:
  - reusable base components, including `PasswordField`, with a button to show the password, and `FileDropzone`, for any tool that receives files;
  - `auth/` (`SessionProvider`, `ProtectedShell`, `AccountMenu` and the login and registration forms) and `account/` (profile);
  - `talento/`, `funciones/`, `incidencias/` and `proveedores/`.
- `hooks/`: custom hooks, including `useSession`.
- `lib/`: `tools.ts`, `format.ts`, `api-client.ts`, `auth/`, and one folder per tool.
- `types/`: API types (`api.ts` for errors and `auth.ts` for users and profiles).

## Known limitations

- **The token lives in `localStorage`:** ticket AUTH-02 requires it, but a script injected into the page could read it. The architecture proposal (5.2) planned a cookie that JavaScript cannot read.
- **Open registration:** `/register` and `POST /users` are public, so anyone can create a `user` account and get in. There are no per-tool permissions yet.
- **The session check runs in the browser:** the server delivers protected views without their content, which only appears after the API validates the token. Real data protection lives in the API.
- **`/funciones` is temporary:** it tests the rules in `@repo/brasa-core`, a transitional package. Once those rules move to the backend, it must be retired or call the API. Do not add business calculations to the frontends.
- **`/incidencias` downloads the API's latest analysis:** it is kept in memory, so if the API restarts the file must be uploaded again, and if two people analyze at the same time, the most recent one is downloaded.
- **`/proveedores` writes to the API's local database:** registrations and rate or status changes are saved in `services/brasaland-api/storage/brasaland-db.json`. To go back to the initial data, delete that file and restart the API. The interface does not offer deleting suppliers: the usual flow is to suspend them.
- **Header height:** `FilterBar` depends on the fixed header height (57 px on mobile and 89 px from `md`). Tool links are hidden on mobile, where staff navigate from the home page. Below `xl`, "Mi perfil" and "Cerrar sesión" are shown as icons only.
- **Shared API:** the tracker uses a shared playground API, so avoid test writes against it. That API is a third party and does not receive the session token.
- **After moving routes, `tsc` may fail on stale `.next` types:** delete `.next`, which is a generated artifact.
