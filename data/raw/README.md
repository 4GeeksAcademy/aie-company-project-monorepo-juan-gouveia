# `data/raw` folder

This folder is intended for **raw data** related to the company: dumps, exports, sample files, event samples, or untransformed datasets.

- **Main purpose**: serve as a landing zone or reference for original data before pipelines process it.
- **Recommendation**: document each dataset’s origin, format, expected size, privacy/PII considerations, and how it is versioned (ideally avoiding sensitive data in the repository).

## Datasets

### `incidents-brasaland.csv`

- **Origin:** test file from the Operations briefing. It is the export of the shared spreadsheet where location managers logged operational incidents.
- **Content:** 100 incidents from January 2024 across the 14 locations (`COL-01`…`COL-10` and `FLA-01`…`FLA-04`). This is test data, with 4 intentionally invalid records.
- **Format:** UTF-8, comma-separated, with a header row. Columns: `incident_id`, `date`, `location_id`, `category`, `description`, `status`, `customer_id`, `satisfaction_score` and `reporter_id`.
- **Privacy:** customer (`CLI-XXXXXX`) and manager (`MGR-XX`) IDs are codes, with no names or contact details.
- **Versioning:** kept exactly as received; do not modify it. It is processed by [`scripts/incident-report/`](../../scripts/incident-report/README.md).

### `telemetry_events/` (business pipeline, outside Git)

- **Origin:** the optional `save_raw_extract` task of the [weekly performance pipeline](../pipelines/README.md) saves each run's extract here, as `<run_id>.json`. The source is `telemetry_events`, in Supabase; this copy is for auditing what a run read.
- **Content:** the weeks, the environment and the business events read (`id`, `timestamp`, `event_type` and the business properties in `tags`).
- **Privacy:** no `user_id`, `session_id` or `request_id` (telemetry plan, §8).
- **Versioning:** ignored by Git (root `.gitignore`). It can be deleted: the pipeline never reads it.

### `telemetry_exports/` (nightly script, outside Git)

- **Origin:** [`scripts/nightly_export.py`](../../scripts/README.md#nightly_exportpy) (ticket #DEV-53) exports every night the previous day's (UTC) `telemetry_events` rows to `telemetry_YYYY-MM-DD.csv`, only if the file does not exist. It is a backup for auditing and recovery: the pipeline reads from the database, not from these files.
- **Content:** all of the day's rows, from any environment, with the table's columns: `id`, `timestamp` (UTC, ISO 8601), `service`, `event_type`, `level`, `value`, `message` and `tags` (JSON with sorted keys). A day without events leaves only the header.
- **Privacy:** `tags` keeps `user_id`, `session_id` and `request_id` (the telemetry plan's pseudonyms), because it is a full copy of the table.
- **Versioning:** ignored by Git (root `.gitignore`). An existing file is never overwritten; to export a day again, delete it first.

> _Spanish version: [README.es.md](./README.es.md)._
