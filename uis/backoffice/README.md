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
NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/telemetry/events  # telemetry receiver
NEXT_PUBLIC_TELEMETRY_ENVIRONMENT=development     # environment of the events
```

Tools that use the Brasaland API need it to be running; see [`services/brasaland-api/README.md`](../../services/brasaland-api/README.md).

Then run:

```bash
npm install
npm run dev     # http://localhost:3001
npm run lint
npm run build
npm test                # Jest unit tests (__tests__/)
npm run test:coverage   # the same, with coverage (report in coverage/)
npm run telemetry:catalog  # regenerates lib/telemetry/catalog.ts after changing docs/telemetry/event-schemas.json
```

`npm install` links `@repo/brasa-core` from `packages/brasa-core`, so run it again after a fresh clone.

The Jest tests cover the authentication logic in `lib/auth/` (`__tests__/auth/`, ticket AUTH-088), the `lib/format.ts`, `toUserMessage` and `readJson` utilities (`__tests__/utils/`, ticket FE-019) and the inventory section (`__tests__/inventory/`, ticket BRD-0512): `lib/inventory.ts` calls with a mocked `fetch`, stock levels, form validation and the merged order history. The telemetry service has its own in `__tests__/telemetry/` (queue, sending, envelope, session, validation and catalog). Each folder runs on its own with `npm test -- __tests__/auth`, `__tests__/utils`, `__tests__/inventory` or `__tests__/telemetry`. What each file tests and its coverage are in [`services/brasaland-api/TESTING.md`](../../services/brasaland-api/TESTING.md#backoffice-tests-jest) and in its FE-019 section.

## Session

Every view requires a session except `/login`, `/register` (ticket AUTH-02), `/forgot-password` and `/reset-password` (ticket AUTH-03). The public website (`uis/website`) is not affected.

| Route | View |
|---|---|
| `/login` | Email and password (with a button to show it). Stores the token and returns to the `?next=` route (internal routes only), or to `/`. Shows a notice if the session expired (`?reason=expired`), the account is deactivated (`?reason=inactive`) or after a password reset (`?reset=success`). It has the "¿Olvidaste tu contraseña?" link |
| `/register` | Email, password (with a button to show it) and an optional profile (full name, phone and address). Calls `POST /users` and then `POST /auth/login`. API errors are shown next to each field |
| `/forgot-password` | Email. Calls `POST /auth/forgot-password` and always shows "Si esa dirección está registrada, recibirás un enlace en breve", without revealing whether the account exists. After sending, the form is disabled. If the request does not reach the API (no connection), it shows the error and lets the user retry |
| `/reset-password` | Opens the email link (`?token=`). It checks the link on load (`POST /auth/reset-password/validate`): if it is not valid, expired or already used, it shows the error and "Solicitar un nuevo enlace". If it works, it asks for the new password and its confirmation (they must match before calling the API), calls `POST /auth/reset-password` and returns to `/login?reset=success`. It does not send the URL with the token as `Referer` (`referrer: no-referrer`) |
| `/account/profile` | Requires a session. Shows the email and profile (from `GET /auth/me`) and lets the user edit full name, phone and address with `PUT /profiles/me`. Only changed fields are sent; an empty field is cleared. Saving updates the name in the header. It links to `/account/change-password` |
| `/account/change-password` | Requires a session. Current password, new password and confirmation (they must match before calling the API). Calls `POST /auth/change-password`: on success it stores the new token the API returns (earlier sessions stop working), clears the form and shows "Contraseña actualizada."; a wrong current password (400) is shown next to that field |

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
| `/` | Home page with the tools grouped in the same sections as the menu (Inventario, Proveedores, Incidencias and Herramientas), one card per tool | `lib/tools.ts` |
| `/talento` | Talent Pipeline Tracker: candidates, status, stage, and notes. The candidate form is lazy loaded (`next/dynamic`) when opened | REST API |
| `/incidencias` | Incident analysis: uploads the Operations CSV, shows the summary and the invalid records with their reason, and downloads `results.csv` | Brasaland API, through the intermediary |
| `/gestor-incidencias` | Incident manager: summary (totals by status, category, origin and location, from `GET /incidents/summary`) and a list filtered by `status`, `origin` and `branch`, newest first. Each block has its own loading state and error with "Reintentar", so a summary failure does not break the list. An empty list and "no results for the filters" have their own message. Each incident changes status from the list (valid transitions only): the change shows at once and, if the API rejects it or fails, it goes back to the previous status and warns. Dates are shown in UTC, because the history was loaded as midnight UTC. The list renders 50 incidents and 50 more with "Mostrar más"; it goes back to 50 when a filter changes, not when a status changes | Brasaland API (`incidents` domain, TinyDB), through the intermediary |
| `/gestor-incidencias/nueva` | Register an incident (centralized incident manager): title, description, category, origin and location, with large fields for tablets. It validates the required fields before sending; with `origin = branch` it highlights the location; the location drop-down shows the briefing names ("Medellín Centro"). While sending, the button is disabled with a loading indicator; API errors appear next to their field and, after success, the form is cleared and confirms. Every new incident starts as `open` | Brasaland API (`incidents` domain, TinyDB), through the intermediary |
| `/proveedores` | Supplier directory: list of active and suspended suppliers, country and category filters, registration, rate updates and activating or suspending. The registration form is lazy loaded (`next/dynamic`) when opened | Brasaland API (`suppliers` domain, TinyDB), through the intermediary |
| `/inventario/ingredientes` | Inventory (Milestone 5): ingredients with SKU, category, country, unit and current stock, with its level (out of stock, low or healthy; per-unit thresholds in `lib/inventory-stock-level.ts`) and a legend. Each row opens the inbound or outbound form with that ingredient selected (`?ingredient_id=`). `/inventario` redirects here | Brasaland API (`inventory` domain, Supabase), through the intermediary |
| `/inventario/ordenes/entrada` | Record an inbound order: ingredient (by name, with SKU and unit), quantity, supplier (one of the active suppliers in the directory for the ingredient's country and category; if there are none, an alert links to the directory) and location. Validates before sending; API errors appear next to their field or in an alert; on success it confirms and clears | Same |
| `/inventario/ordenes/salida` | Record an outbound order: ingredient, quantity, reason (`consumption` or `waste`) and location. Shows the current stock when the ingredient is chosen, warns without blocking if the quantity exceeds it, and shows the insufficient-stock 400 next to the quantity | Same |
| `/inventario/ordenes` | Read-only order history: inbound and outbound orders together, newest first, with type, ingredient, quantity, supplier or reason, location, date and user (`user_uuid`, with "Tú" on your own). Filters by type and ingredient (name or SKU, accent-insensitive), applied in the browser and memoized. It renders 50 orders and 50 more with "Mostrar más" | Same |
| `/funciones` | Manual tests for filters, search, reports, and validations | `@repo/brasa-core` sample data |
| `/telemetria` | Technical telemetry (technical report, admins only): the report period and one block per metric. `events_per_day`, with one bar per day stacked by level; `error_rate_by_type`, `api_latency_by_route` (with a bar for the mean) and `auth_failure_rate`, as tables. Two optional dates in UTC, both included (the end is sent as the next day, because the API treats it as exclusive) and "Últimos 7 días". Non-admins see "Solo los administradores pueden ver el reporte técnico." Bars built with Tailwind, no chart library | The API's `GET /telemetry/report`, through `app/api/telemetry/report/route.ts` |

## Adding a tool

1. Create its route in `app/(protegido)/<tool>/`, so it requires a session. The group does not change the URL.
2. Put its own files in `components/<tool>/` and `lib/<tool>/`. Reusable pieces stay directly in `components/`.
3. Add an entry to `lib/tools.ts`, inside its section in `toolSections`. The home page and navigation are generated from that list: a section with a single tool is a direct link in the header; one with several is a dropdown (`components/NavDropdown.tsx`).

Internal areas, including training, join this project as tools, not as separate applications. Later on, each `lib/tools.ts` entry may declare the permission it needs, and the list will be filtered with `GET /auth/me`. That filter will only affect the interface: real authorization lives in the API.

Calls to the Brasaland API go through `apiJson` or `apiFetch` in `lib/api-client.ts`, which add the token, turn errors into an `ApiError` (`status`, `code`, `message`, per-field `details`) and end the session on a 401.

## Telemetry

The backoffice captures usage events with its own service, `lib/telemetry/` ([telemetry plan](../../docs/telemetry/telemetry-plan.md), section 13). **All tracking goes through a single function**:

```ts
import { track } from "@/lib/telemetry";

track("page_viewed", { route: "/inventario/ordenes", navigation_type: "client" });
```

- **Callers only pass the type and the properties.** The service adds the envelope: `eventId` (UUID generated at capture time), the capture `timestamp`, `sessionId`, `userId`, the `schemaVersion` of that event's schema, `requestId`, `source: "browser"` and `environment`.
- **Allowlist.** `track()` checks every event against `lib/telemetry/catalog.ts`, generated from `docs/telemetry/event-schemas.json` (`npm run telemetry:catalog`). An unknown type, a missing required property or a key outside the allowlist drops the event, with a console warning in development.
- **Batched sending.** Events pile up in memory and go to `NEXT_PUBLIC_TELEMETRY_ENDPOINT` every 10 seconds or when 20 accumulate, whichever comes first. If sending fails, it retries 3 times (1, 2 and 4 s waits) and then drops the batch. When the tab is hidden or closed, whatever is pending goes out with `navigator.sendBeacon`. Without the variable, telemetry is disabled.
- **Session.** `sessionId` is created at login and kept in `sessionStorage` (one per tab). `userId` is the token's `sub` (the account UUID, never the email). Without a session, both are `null`.
- **Correlation.** `apiFetch` sends a new UUID in `X-Request-Id` with every call; the intermediary forwards it and the API writes it to its log. Events born from an API response carry that `requestId`, which the data layer sets with `withRequestId()` (`lib/telemetry/request-context.ts`).
- **Where it is instrumented.** Never in components, always in the data layer:
  - `lib/inventory.ts` emits the mandatory order metrics on the API's 201: `inbound_order_created`, `ingredient_price_variance_detected` (with the `GET /inventory/orders` history), `outbound_order_created` or `stock_waste_registered` depending on the reason, and `stock_threshold_triggered` when the low-stock threshold is crossed. The calculations live in `lib/telemetry/inventory-events.ts`;
  - `lib/api-client.ts` passes every call to `lib/telemetry/api-events.ts`: `api_latency_recorded` (always the slow and failed ones, 1 in 10 of the rest) and, on errors, `api_error_returned` (4xx), `api_connection_failed` (502, 504 or 500 from the intermediary), `order_validation_failed`, `direct_stock_edit_rejected` when the API rejects a direct stock change (the 405 from "Ajustar stock" or a 422 for `current_stock`), `session_expired` and `auth_token_rejected` (session 401s, one per token every 60 s) and `password_reset_link_rejected`;
  - `lib/proveedores/api.ts`, `lib/gestor-incidencias/api.ts` and `lib/incidencias/api.ts` emit `supplier_created`, `supplier_rate_updated`, `supplier_status_changed`, `incident_created`, `incident_status_changed`, `incident_transition_rejected` and `incident_report_analyzed` (calculations in `lib/telemetry/business-events.ts`); `lib/inventory.ts` also emits `outbound_order_rejected`;
  - the entry, exit, incident, supplier, login and registration forms use `useFormTelemetry` (`form_validation_failed` and `form_abandoned`, field names only), and the history, manager and directory use `useListFilterTelemetry` (`list_filter_applied`) and `useShowMore` (`list_page_extended`);
  - `lib/auth/api.ts` and `SessionProvider` emit authentication: `login_failed` (`invalid_credentials`, `inactive_user` or `network_error`, never the email or password), `login_succeeded` (when the session is validated, with the role), `logout_completed`, `user_registered`, `password_reset_completed` and `password_changed`;
  - `components/telemetry/TelemetryRoot.tsx`, in the root layout, emits `page_viewed` on every view, `frontend_error_captured` for `window.onerror` and `unhandledrejection` (the `error.tsx` and `global-error.tsx` screens emit it through `useReportBoundaryError`) and collects Web Vitals with `useReportWebVitals`: LCP, CLS and INP go out in one `page_performance_recorded` per load, when the tab is hidden and before the `sendBeacon` (`lib/telemetry/lifecycle.ts`).
- **Receiver.** The URL points straight at the API (`http://localhost:8000/telemetry/events`), not through the intermediary: it is the browser's only call to another origin, and the API allows CORS just for it.

## Structure

- `app/`: root layout (no header) and two route groups:
  - `(protegido)/`: home page and one folder per tool, with the session guard;
  - `(publico)/`: `login/` and `register/`, with a header without navigation.
- `app/api/[...path]/route.ts`: intermediary (BFF) to the Brasaland API. The forwarding lives in `lib/bff/proxy.ts`, shared with `app/api/telemetry/report/route.ts`: the telemetry technical report, which the API serves outside `/api/v1`, is forwarded to the origin of `API_BASE_URL` (`http://localhost:8000/telemetry/report`). Next.js picks that route before the catch-all.
  - It forwards `GET`, `POST`, `PUT`, `PATCH` and `DELETE` on `/api/<path>` to `API_BASE_URL/<path>`, with the `Content-Type`, `Accept`, `Authorization` and `X-Request-Id` headers, applying no logic. From the response it copies `Content-Type`, `Content-Disposition`, `X-Request-Id` and `X-Cache`.
  - The API URL stays on the server and CORS is not needed.
  - If the variable is missing it returns 500 (`api_not_configured`); if the API does not respond, 502 (`api_unavailable`); if it takes longer than 15 seconds, it cuts the request and returns 504 (`api_timeout`). In all three cases the user gets a generic message, and the server log records a `[BFF]` line with the method, the path (without query) and the cause; never headers or body.
- `components/`:
  - reusable base components, including `PasswordField`, with a button to show the password, `FileDropzone`, for any tool that receives files, and `TextAreaField`. `FormField`, `TextAreaField` and `LabeledSelect` accept `size="lg"` for touch forms;
  - `auth/` (`SessionProvider`, `ProtectedShell`, `AccountMenu` and the login, registration and password recovery forms) and `account/` (profile and password change);
  - `talento/`, `funciones/`, `incidencias/`, `gestor-incidencias/`, `proveedores/`, `inventario/` and `telemetria/` (the technical report view; `telemetry/` is event capture).
- `hooks/`: custom hooks, including `useSession` and `useShowMore` (long lists rendered in parts).
- `lib/`: `tools.ts`, `format.ts`, `api-client.ts`, `auth/`, `telemetry/` (telemetry service; see [Telemetry](#telemetry)), `bff/proxy.ts` (proxy forwarding), `telemetry-report.ts` (technical report client and formatting), and one folder per tool. The inventory uses `lib/inventory*.ts` files: `inventory.ts` is its integration module, the only one that calls `/api/inventory/...`.
- `scripts/generate-telemetry-catalog.mjs`: generates `lib/telemetry/catalog.ts` from `docs/telemetry/event-schemas.json`.
- `types/`: API types (`api.ts` for errors and `auth.ts` for users and profiles).

## Known limitations

- **The token lives in `localStorage`:** ticket AUTH-02 requires it, but a script injected into the page could read it. The architecture proposal (5.2) planned a cookie that JavaScript cannot read.
- **Open registration:** `/register` and `POST /users` are public, so anyone can create a `user` account and get in. There are no per-tool permissions yet.
- **The session check runs in the browser:** the server delivers protected views without their content, which only appears after the API validates the token. Real data protection lives in the API.
- **`/funciones` is temporary:** it tests the rules in `@repo/brasa-core`, a transitional package. Once those rules move to the backend, it must be retired or call the API. Do not add business calculations to the frontends. Being a developer tool, an unexpected error shows a readable message plus the technical error (`detail`), instead of hiding it like the rest of the backoffice does.
- **`/incidencias` downloads the API's latest analysis:** it is kept in memory, so if the API restarts the file must be uploaded again, and if two people analyze at the same time, the most recent one is downloaded.
- **`/proveedores` writes to the API's local database:** registrations and rate or status changes are saved in `services/brasaland-api/storage/brasaland-db.json`. To go back to the initial data, delete that file and restart the API. The interface does not offer deleting suppliers: the usual flow is to suspend them.
- **`/inventario` writes to the API's database:** with the API configured against Supabase, every inbound or outbound order changes the real stock and cannot be deleted (it is corrected with a compensating order). For testing, start the API with a temporary `DATABASE_URL` (for example, SQLite). The outbound stock refreshes when the ingredient is chosen and after each submission, not in real time: the API applies the rule with the stock at that moment.
- **Header height:** `FilterBar` depends on the fixed header height (57 px on mobile and 89 px from `md`). From `xl`, the header shows the menu by sections; below that it does not fit next to the account, so a hamburger menu (`components/MobileNav.tsx`) is used, whose panel overlays the page under the header without changing its height. "Mi perfil" and "Cerrar sesión" are shown as icons only at every size; on desktop, a tooltip (`components/Tooltip.tsx`) shows the user's name (or email) and "Cerrar sesión" on hover or keyboard focus.
- **Shared API:** the tracker uses a shared playground API, so avoid test writes against it. That API is a third party and does not receive the session token.
- **After moving routes, `tsc` may fail on stale `.next` types:** delete `.next`, which is a generated artifact.
