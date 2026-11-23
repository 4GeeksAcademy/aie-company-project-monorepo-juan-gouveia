# `data/eval` folder

This folder is for **evaluation and validation**: evaluation datasets, golden sets, experiment results, metrics, and artifacts used to measure quality for models, RAG, agents, or pipelines.

- **Main purpose**: centralize evaluation inputs and outputs so improvements stay measurable across project milestones.
- **Recommendation**: document each evaluation set (what it measures, how it was built, success criteria) and avoid sensitive data; use synthetic or anonymized data when needed.

## Sets

### `weekly_location_performance/` (business pipeline, outside Git)

- **Origin:** the optional `export_eval_snapshot` task of the [weekly performance pipeline](../pipelines/README.md) writes `<run_id>.json` here at the end of each run.
- **What it measures:** five quality checks on the rows written to `reporting.weekly_location_performance`: 14 rows per week, `waste_ratio` consistent with the costs, the currency matching the country, no negative values and every row written. It includes the rows and the run counts (events read, rejected and discarded by reason).
- **Success criterion:** every check is `true`.
- **Versioning:** ignored by Git (root `.gitignore`). If the export fails, the run carries on and records it in its log (`export_eval_snapshot_failed`).

> _Spanish version: [README.es.md](./README.es.md)._
