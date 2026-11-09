"""Pruebas de analyze.py.

Uso (desde esta carpeta):
    python -m unittest -v
"""

import contextlib
import csv
import io
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import analyze

SOURCE = analyze.RAW_DIR / "incidents-brasaland.csv"


def make_record(**overrides):
    """Registro válido de un caso abierto; los argumentos cambian campos concretos."""
    record = {
        "incident_id": "BRS-000001",
        "date": "2024-01-01",
        "location_id": "COL-01",
        "category": "STAFF",
        "description": "Descripción válida",
        "status": "OPEN",
        "customer_id": "",
        "satisfaction_score": "",
        "reporter_id": "MGR-01",
    }
    record.update(overrides)
    return record


class BriefingValuesTest(unittest.TestCase):
    """Los resultados del CSV provisto deben coincidir exactamente con el briefing."""

    @classmethod
    def setUpClass(cls):
        cls.summary = analyze.analyze(analyze.load_records(SOURCE))

    def test_totals(self):
        self.assertEqual(self.summary["total"], 100)
        self.assertEqual(self.summary["valid"], 96)
        self.assertEqual(self.summary["invalid"], 4)

    def test_invalid_breakdown(self):
        self.assertEqual(self.summary["rules"], {
            "missing_location": 1,
            "invalid_category": 1,
            "empty_description": 1,
            "missing_reporter": 0,
            "invalid_status": 0,
            "closed_without_score": 1,
            "score_out_of_range": 0,
        })

    def test_categories(self):
        self.assertEqual(self.summary["categories"], {
            "CUSTOMER_COMPLAINT": 29,
            "EQUIPMENT": 17,
            "SUPPLY": 22,
            "FOOD_QUALITY": 19,
            "STAFF": 9,
        })

    def test_statuses(self):
        self.assertEqual(self.summary["statuses"], {"OPEN": 32, "CLOSED": 50, "DISCARDED": 14})

    def test_satisfaction(self):
        self.assertEqual(self.summary["closed_cases"], 50)
        self.assertEqual(self.summary["scored_cases"], 50)
        self.assertEqual(self.summary["scores"], {1: 4, 2: 6, 3: 12, 4: 19, 5: 9})
        self.assertEqual(analyze.rounded_average(self.summary), Decimal("3.46"))

    def test_report_shows_briefing_values(self):
        report = analyze.format_report(self.summary, SOURCE.name)
        for expected in [
            "Source file: incidents-brasaland.csv",
            "(30.2%)", "(17.7%)", "(22.9%)", "(19.8%)", "(9.4%)",
            "(33.3%)", "(52.1%)", "(14.6%)",
            "Scored cases: 50 of 50",
            "Average score: 3.46 / 5.00",
        ]:
            self.assertIn(expected, report)

    def test_invalid_details(self):
        self.assertEqual(self.summary["invalid_details"], [
            {"incident_id": "BRS-000044", "row": 45, "rules": ["missing_location"]},
            {"incident_id": "BRS-000049", "row": 50, "rules": ["invalid_category"]},
            {"incident_id": "BRS-000079", "row": 80, "rules": ["empty_description"]},
            {"incident_id": "BRS-000086", "row": 87, "rules": ["closed_without_score"]},
        ])

    def test_report_lists_invalid_records(self):
        report = analyze.format_report(self.summary, SOURCE.name)
        self.assertIn("INVALID RECORDS DETAIL", report)
        self.assertIn("  ├─ BRS-000044 (row 45): Missing location_id", report)
        self.assertIn("  └─ BRS-000086 (row 87): Closed case, no score", report)

    def test_report_hides_rules_without_cases(self):
        report = analyze.format_report(self.summary, SOURCE.name)
        self.assertIn("Missing location_id", report)
        self.assertNotIn("Missing reporter_id", report)
        self.assertNotIn("Score out of range", report)
        self.assertNotIn("Note:", report)


class ValidationRulesTest(unittest.TestCase):

    def assertBroken(self, record, expected):
        self.assertEqual(analyze.validate_record(record), expected)

    def test_valid_records(self):
        self.assertBroken(make_record(), [])
        self.assertBroken(make_record(description="Cinco"), [])
        self.assertBroken(make_record(location_id="FLA-04", status="CLOSED", satisfaction_score="1"), [])
        self.assertBroken(make_record(location_id="COL-10", status="CLOSED", satisfaction_score="5"), [])
        self.assertBroken(make_record(status="DISCARDED"), [])

    def test_location(self):
        self.assertBroken(make_record(location_id=""), ["missing_location"])
        self.assertBroken(make_record(location_id="COL-11"), ["missing_location"])
        self.assertBroken(make_record(location_id="FLA-05"), ["missing_location"])

    def test_category(self):
        self.assertBroken(make_record(category=""), ["invalid_category"])
        self.assertBroken(make_record(category="OTHER"), ["invalid_category"])

    def test_description(self):
        self.assertBroken(make_record(description=""), ["empty_description"])
        self.assertBroken(make_record(description="Cuat"), ["empty_description"])

    def test_reporter(self):
        self.assertBroken(make_record(reporter_id=""), ["missing_reporter"])

    def test_status(self):
        self.assertBroken(make_record(status="PENDING"), ["invalid_status"])
        self.assertBroken(make_record(status=""), ["invalid_status"])

    def test_closed_without_score(self):
        self.assertBroken(make_record(status="CLOSED"), ["closed_without_score"])

    def test_score_out_of_range(self):
        for score in ["0", "6", "abc", "4.5", "-1"]:
            with self.subTest(score=score):
                self.assertBroken(make_record(status="CLOSED", satisfaction_score=score), ["score_out_of_range"])

    def test_record_breaking_several_rules_counts_once_in_total(self):
        records = [
            make_record(),
            make_record(location_id="", category="", description="", status="CLOSED"),
        ]
        summary = analyze.analyze(records)
        self.assertEqual(summary["invalid"], 1)
        self.assertEqual(summary["rules"]["missing_location"], 1)
        self.assertEqual(summary["rules"]["closed_without_score"], 1)
        self.assertIn("Note:", analyze.format_report(summary, "test.csv"))

    def test_detail_joins_several_rules_and_handles_missing_id(self):
        records = [make_record(), make_record(incident_id="", location_id="", category="")]
        summary = analyze.analyze(records)
        self.assertEqual(summary["invalid_details"], [
            {"incident_id": "", "row": 3, "rules": ["missing_location", "invalid_category"]},
        ])
        report = analyze.format_report(summary, "test.csv")
        self.assertIn("  └─ (no id) (row 3): Missing location_id; Invalid or missing category", report)

    def test_no_detail_section_without_invalid_records(self):
        report = analyze.format_report(analyze.analyze([make_record()]), "test.csv")
        self.assertNotIn("INVALID RECORDS DETAIL", report)


class EdgeCasesTest(unittest.TestCase):

    def test_no_valid_records(self):
        summary = analyze.analyze([make_record(location_id="")])
        self.assertIsNone(summary["average_score"])
        report = analyze.format_report(summary, "test.csv")
        self.assertIn("(n/a)", report)
        self.assertIn("Average score: n/a", report)

    def test_percentage_rounds_half_up(self):
        self.assertEqual(analyze.percentage(9, 400), Decimal("2.3"))
        self.assertEqual(analyze.percentage(9, 96), Decimal("9.4"))
        self.assertIsNone(analyze.percentage(1, 0))


class LoadingTest(unittest.TestCase):

    def test_resolve_source_falls_back_to_raw_dir(self):
        self.assertEqual(analyze.resolve_source("incidents-brasaland.csv"), SOURCE)

    def test_resolve_source_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            analyze.resolve_source("no-existe.csv")

    def test_load_strips_spaces_and_bom(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bom.csv"
            path.write_text(
                ",".join(analyze.FIELDS) + "\n"
                "BRS-000001,2024-01-01, COL-01 ,STAFF,Con BOM,OPEN,,,MGR-01\n",
                encoding="utf-8-sig",
            )
            records = analyze.load_records(path)
        self.assertEqual(records[0]["incident_id"], "BRS-000001")
        self.assertEqual(records[0]["location_id"], "COL-01")

    def test_load_missing_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "faltan.csv"
            path.write_text("incident_id,date\nBRS-000001,2024-01-01\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                analyze.load_records(path)


class ExportTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = analyze.build_export_rows(analyze.analyze(analyze.load_records(SOURCE)))
        cls.by_metric = {row["metric"]: row for row in cls.rows}

    def test_one_row_per_metric(self):
        self.assertEqual(len(self.by_metric), len(self.rows))

    def test_all_rules_present_even_at_zero(self):
        for key, _ in analyze.RULES:
            self.assertIn(f"invalid.{key}", self.by_metric)
        self.assertEqual(self.by_metric["invalid.missing_reporter"]["value"], 0)

    def test_values_match_briefing(self):
        self.assertEqual(self.by_metric["valid_records"]["value"], 96)
        self.assertEqual(self.by_metric["category.STAFF"]["percentage"], Decimal("9.4"))
        self.assertEqual(self.by_metric["status.CLOSED"]["value"], 50)
        self.assertEqual(self.by_metric["satisfaction.average"]["value"], Decimal("3.46"))
        self.assertEqual(self.by_metric["total_records"]["percentage"], "")

    def test_export_csv_writes_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = analyze.export_csv(self.rows, Path(folder) / "nested" / "results.csv")
            with open(path, encoding="utf-8", newline="") as file:
                written = list(csv.DictReader(file))
        self.assertEqual(list(written[0].keys()), analyze.EXPORT_COLUMNS)
        self.assertEqual(len(written), len(self.rows))
        self.assertEqual(written[0], {"metric": "total_records", "value": "100", "percentage": ""})

    def test_wants_export_answers(self):
        for answer, expected in [("s", True), ("Sí", True), (" yes ", True), ("n", False), ("", False)]:
            with self.subTest(answer=answer), patch("builtins.input", return_value=answer):
                self.assertIs(analyze.wants_export(), expected)

    def test_main_reports_export_write_error_without_traceback(self):
        # results.csv abierto en Excel: Windows impide escribirlo y open() lanza PermissionError.
        locked = PermissionError(13, "Permission denied", str(analyze.EXPORT_PATH))
        stderr = io.StringIO()
        with (
            patch("analyze.export_csv", side_effect=locked),
            patch("builtins.input", return_value="y"),
            patch("sys.stdout", io.TextIOWrapper(io.BytesIO())),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(analyze.main([str(SOURCE)]), 1)
        self.assertIn("could not write", stderr.getvalue())
        self.assertIn("Permission denied", stderr.getvalue())
        self.assertIn("close it", stderr.getvalue())

    def run_main_expecting_error(self, side_effect):
        stderr = io.StringIO()
        with patch("analyze.load_records", side_effect=side_effect), contextlib.redirect_stderr(stderr):
            self.assertEqual(analyze.main([str(SOURCE)]), 1)
        return stderr.getvalue()

    def test_main_reports_read_error_without_traceback(self):
        message = self.run_main_expecting_error(PermissionError(13, "Permission denied", str(SOURCE)))
        self.assertIn("could not read", message)
        self.assertIn("Permission denied", message)

    def test_main_reports_non_utf8_file_clearly(self):
        decode_error = UnicodeDecodeError("utf-8", b"\xf3", 0, 1, "invalid continuation byte")
        message = self.run_main_expecting_error(decode_error)
        self.assertIn("is not valid UTF-8", message)
        self.assertNotIn("codec", message)

    def test_main_ctrl_c_at_export_prompt_cancels_without_traceback(self):
        stderr = io.StringIO()
        with (
            patch("builtins.input", side_effect=KeyboardInterrupt),
            patch("analyze.export_csv") as export_csv,
            patch("sys.stdout", io.TextIOWrapper(io.BytesIO())),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(analyze.main([str(SOURCE)]), 130)
        export_csv.assert_not_called()
        self.assertIn("Export cancelled.", stderr.getvalue())

    def test_wants_export_without_input(self):
        with patch("builtins.input", side_effect=EOFError), patch("builtins.print"):
            self.assertFalse(analyze.wants_export())


if __name__ == "__main__":
    unittest.main()
