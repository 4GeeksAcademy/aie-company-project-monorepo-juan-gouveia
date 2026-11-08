# Shared package (`packages/shared`)

Code reused across the monorepo's projects. It has two independent parts:

| Part | Language | Contents | Consumed by |
|---|---|---|---|
| `brasaland_shared/` (package `brasaland-shared`) | Python, standard library only | Rules for the legacy system's incidents CSV: validation, analysis and file errors | `scripts/incident-report/analyze.py`, `scripts/seed_incidents.py` and `services/brasaland-api` |
| `types/` (package `@repo/shared-types`) | TypeScript | Base types (`Id`, `BaseEntity`) | Not consumed yet |

> _Spanish version: [README.es.md](./README.es.md)._

## `brasaland_shared.incidents`

It is the **only** implementation of the incidents CSV rules (`incidents-brasaland.csv`). The analyzer, the incident manager seed and the API import it; none of them has a copy.

| Module | Contents |
|---|---|
| `validation.py` | Columns (`FIELDS`), allowed values (`LOCATIONS`, `CATEGORIES`, `STATUSES`), invalidity rules (`RULES`, `RULE_LABELS`), reading (`parse_records`, `load_records`, `parse_upload`) and `validate_record` / `split_records` |
| `analysis.py` | Report metrics (`analyze`, `percentage`, `rounded_average`) and export (`build_export_rows`, `export_csv_text`) |
| `exceptions.py` | Errors for a file that cannot be analyzed (`EmptyFileError`, `InvalidEncodingError`, `MissingColumnsError`, `NoRecordsError`) |

### How it is consumed

- **Scripts:** they add `packages/shared` to the Python path and import `brasaland_shared`. Since the package has no dependencies, nothing needs to be installed.
- **API:** it declares it as a local dependency in its `pyproject.toml` (`[tool.uv.sources]`, editable mode), so `uv sync` installs it and changes are picked up without reinstalling. `app/domains/incidents/service.py` and `exceptions.py` only re-export what the analyzer uses.

### Why here

The incident manager assignment requires the previous project's validation to live in `packages/shared/` and to be reused by the script and the API without duplication. It used to live in `services/brasaland-api/app/domains/incidents/service.py`; it was moved without changing any rule, and the analyzer tests (32 in the script and 24 in the API) pass unmodified.

### Tests

The rules are tested through their consumers: the script tests (`scripts/incident-report/test_analyze.py`), the API analyzer tests (`tests/domains/incidents/test_service.py` and `test_router.py`) and the seed tests (`scripts/test_seed_incidents.py`).
