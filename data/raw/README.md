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

> _Spanish version: [README.es.md](./README.es.md)._
