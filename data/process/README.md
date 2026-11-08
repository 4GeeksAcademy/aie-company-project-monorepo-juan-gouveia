# `data/process` folder

This folder contains **processed/intermediate data** and/or artifacts produced by pipelines (for example: clean datasets, features, aggregates, intermediate tables, or transformation outputs).

- **Main purpose**: clearly separate “raw” data from data ready for analysis, modeling, or app consumption.
- **Recommendation**: document which pipeline produces each artifact, its schema, refresh cadence, and how quality is validated (checks, constraints, data tests).

## Artifacts

### `results.csv`

- **Produced by:** [`scripts/incident-report/analyze.py`](../../scripts/incident-report/README.md), when the export prompt is answered with yes.
- **Schema:** one row per metric, with the columns `metric`, `value` and `percentage`. The list of metrics is in the script's README.
- **Refresh:** each run overwrites the previous file.
- **Quality:** the script's tests (`python -m unittest`) check the values against the dataset in `data/raw/`.
- **Versioning:** not committed to Git (it is in `.gitignore`), because every run regenerates it.

> _Spanish version: [README.es.md](./README.es.md)._
