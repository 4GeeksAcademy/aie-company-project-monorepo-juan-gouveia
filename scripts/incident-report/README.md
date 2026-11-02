# Incident report processor (`scripts/incident-report`)

A console script that validates and summarizes Brasaland's operational incidents CSV: equipment failures, supply issues, customer complaints, food quality and staff. Operations runs it before the morning meeting, and its data will feed the future operations dashboard.

## Requirements

- Python 3 (tested with 3.12).
- No external dependencies: it only uses the standard library (`csv`, `decimal`, `unittest`).

## Usage

From this folder:

```bash
python analyze.py incidents-brasaland.csv
```

From the repository root:

```bash
python scripts/incident-report/analyze.py data/raw/incidents-brasaland.csv
```

The path is resolved from the current folder. If it does not exist there, the script looks for the same name in `data/raw/`. If the file cannot be found, or the CSV is missing columns, it prints an error and exits with code 1.

## What it does

1. Reads the CSV (UTF-8, with or without BOM) and checks that it has the 9 expected columns.
2. Marks a record as invalid if it breaks any of these rules:

   | Rule | Condition |
   |---|---|
   | `missing_location` | `location_id` is empty or not one of `COL-01`…`COL-10` and `FLA-01`…`FLA-04` |
   | `invalid_category` | `category` is empty or not one of `CUSTOMER_COMPLAINT`, `EQUIPMENT`, `SUPPLY`, `FOOD_QUALITY` and `STAFF` |
   | `empty_description` | `description` has fewer than 5 characters |
   | `missing_reporter` | `reporter_id` is empty |
   | `invalid_status` | `status` is not `OPEN`, `CLOSED` or `DISCARDED`. This rule is not in the briefing: it keeps an unknown status from counting as valid |
   | `closed_without_score` | `status = CLOSED` with no `satisfaction_score` |
   | `score_out_of_range` | There is a score, but it is not an integer from 1 to 5 |

   A record that breaks several rules counts toward each of them, but only once in the invalid total.
3. For valid records, it counts records per category and per status, with their percentage, and computes the satisfaction index for closed cases: scored cases, the 1–5 distribution and the average.
4. Prints the summary to the console. The invalid breakdown only lists rules that have cases.
5. Asks `¿Deseas exportar los resultados a CSV? [s / n]`. It accepts `s`, `si`, `sí`, `y` or `yes`; any other answer, or no input, skips the export.

Percentages and the average round half up, for example 2.25 → 2.3.

## Export

The results are saved to `data/process/results.csv`, wherever the command is run from, and overwrite the previous export. The file is ignored by Git.

There is one row per metric, with the columns `metric`, `value` and `percentage`. The last one is empty when it does not apply.

| Metric | Value | Percentage |
|---|---|---|
| `total_records` | Rows in the file | — |
| `valid_records`, `invalid_records` | Records | Of the total |
| `invalid.<rule>` | Records breaking the rule. All 7 rules are always listed, even at 0 | — |
| `category.<CODE>`, `status.<CODE>` | Valid records | Of valid records |
| `satisfaction.closed_cases`, `satisfaction.scored_cases` | Valid closed cases and scored cases | — |
| `satisfaction.average` | Average with 2 decimals | — |
| `satisfaction.score_1` … `score_5` | Cases with that score | Of scored cases |

## Tests

```bash
python -m unittest -v
```

The 28 tests check:

- that the provided CSV gives exactly the values expected by the briefing: 100 records, 96 valid, 4 invalid and a 3.46 average;
- each rule, including its edge cases;
- file loading;
- the export and the final prompt.

## Location

The briefing suggested an `incidents-analysis/` folder at the root. The script lives in `scripts/incident-report/` because the assignment asks for it under `/scripts`, and because the monorepo does not allow loose implementation files at the root.

> _Spanish version: [README.es.md](./README.es.md)._
