# Brasaland backoffice

Internal application where Brasaland staff access their tools from a single place.

It addresses the needs in `CONTEXT.md` for modern internal systems. Its first tools support People and Culture recruiting and the review of business logic.

> _Spanish version: [README.es.md](./README.es.md)._

## Stack

Next.js 16 (App Router), React 19, TypeScript, and Tailwind CSS 4. It is an independent project: it shares no layout with `uis/website`.

## How to run it

Copy `.env.example` as `.env.local` and set the API URL:

```bash
NEXT_PUBLIC_API_BASE_URL=<api-base-url>
```

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
| `/funciones` | Manual tests for filters, search, reports, and validations | `@repo/brasa-core` sample data |

## Adding a tool

1. Create its route in `app/<tool>/`.
2. Put its own files in `components/<tool>/` and `lib/<tool>/`. Reusable pieces stay directly in `components/`.
3. Add an entry to `lib/tools.ts`. The home page and navigation are generated from that list.

Internal areas, including training, join this project as tools, not as separate applications. Once authentication exists, each `lib/tools.ts` entry will declare the permission it needs, and the list will be filtered with `GET /auth/me`. That filter only affects the interface: real authorization lives in the API.

## Structure

- `app/`: root layout, home page, and one folder per tool.
- `components/`: reusable base components, plus `talento/` and `funciones/`.
- `hooks/`: custom hooks.
- `lib/`: `tools.ts`, `format.ts`, and one folder per tool.
- `types/`: API types.

## Known limitations

- **No authentication:** do not publish it until login exists.
- **`/funciones` is temporary:** it tests the rules in `@repo/brasa-core`, a transitional package. Once those rules move to the backend, it must be retired or call the API. Do not add business calculations to the frontends.
- **Header height:** `FilterBar` depends on the fixed header height (57 px on mobile and 89 px from `md`). Tool links are hidden on mobile, where staff navigate from the home page.
- **Shared API:** the tracker uses a shared playground API, so avoid test writes against it.
