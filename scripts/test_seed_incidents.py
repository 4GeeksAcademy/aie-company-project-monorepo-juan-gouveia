"""Pruebas del seed de incidencias (scripts/seed_incidents.py).

Necesitan TinyDB, así que se ejecutan con el entorno de la API, desde la raíz del repositorio:
    uv run --project services/brasaland-api python -m unittest scripts/test_seed_incidents.py
"""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seed_incidents as seed_script  # noqa: E402
from seed_incidents import BRANCH_MAP, CATEGORY_MAP, STATUS_MAP, TransformError, seed, transform  # noqa: E402

from app.core.storage import BRASALAND_DB_PATH_ENV  # noqa: E402
from app.domains.incidents.incident_repository import IncidentRepository  # noqa: E402
from brasaland_shared.incidents.validation import FIELDS, load_records  # noqa: E402

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "incidents-brasaland.csv"

# Valores esperados tras el seed (briefing, "Valores esperados tras el seed").
EXPECTED_STATUS = {"open": 32, "in_progress": 0, "resolved": 50, "discarded": 14}
EXPECTED_CATEGORY = {
    "equipment_failure": 17,
    "supply_issue": 22,
    "customer_complaint": 48,
    "staff_issue": 9,
    "facility_issue": 0,
    "pos_system": 0,
    "delivery_issue": 0,
    "other": 0,
}
EXPECTED_INVALID = ["BRS-000044", "BRS-000049", "BRS-000079", "BRS-000086"]


def row(**changes):
    record = {
        "incident_id": "BRS-900001",
        "date": "2024-01-14",
        "location_id": "COL-07",
        "category": "FOOD_QUALITY",
        "description": "Porción servida menor a la estándar del menú",
        "status": "CLOSED",
        "customer_id": "CLI-471507",
        "satisfaction_score": "5",
        "reporter_id": "MGR-01",
    }
    record.update(changes)
    assert set(record) == set(FIELDS)
    return record


class TempRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "db.json"
        self.repository = IncidentRepository.from_path(self.db_path)

    def tearDown(self):
        self.repository.close()
        self.tmp.cleanup()


class TransformTest(unittest.TestCase):
    def test_maps_are_exactly_the_briefing_ones(self):
        self.assertEqual(
            {key: value.value for key, value in STATUS_MAP.items()},
            {"OPEN": "open", "CLOSED": "resolved", "DISCARDED": "discarded"},
        )
        self.assertEqual(
            {key: value.value for key, value in CATEGORY_MAP.items()},
            {
                "CUSTOMER_COMPLAINT": "customer_complaint",
                "EQUIPMENT": "equipment_failure",
                "SUPPLY": "supply_issue",
                "FOOD_QUALITY": "customer_complaint",
                "STAFF": "staff_issue",
            },
        )
        self.assertEqual(
            {key: value.value for key, value in BRANCH_MAP.items()},
            {
                "COL-01": "medellin_centro",
                "COL-02": "medellin_laureles",
                "COL-03": "medellin_envigado",
                "COL-04": "medellin_bello",
                "COL-05": "medellin_itagui",
                "COL-06": "bogota_chapinero",
                "COL-07": "bogota_usaquen",
                "COL-08": "cali_granada",
                "COL-09": "barranquilla_norte",
                "COL-10": "central",
                "FLA-01": "miami_doral",
                "FLA-02": "miami_hialeah",
                "FLA-03": "miami_kendall",
                "FLA-04": "orlando_international",
            },
        )

    def test_transforms_a_row_as_the_briefing_says(self):
        prepared = transform(row())
        incident = prepared.incident
        self.assertEqual(prepared.source_id, "BRS-900001")
        self.assertEqual(incident.title, "Porción servida menor a la estándar del menú")
        self.assertEqual(incident.description, "Porción servida menor a la estándar del menú")
        self.assertEqual(incident.status.value, "resolved")
        self.assertEqual(incident.category.value, "customer_complaint")
        self.assertEqual(incident.branch.value, "bogota_usaquen")
        self.assertEqual(incident.origin.value, "customer")
        self.assertEqual(prepared.created_at, datetime(2024, 1, 14, tzinfo=timezone.utc))

    def test_title_is_the_first_120_characters_trimmed(self):
        description = "Cámara frigorífica " + "x" * 100 + "   " + "y" * 50
        prepared = transform(row(description=description))
        self.assertEqual(prepared.incident.title, description[:120].strip())
        self.assertLessEqual(len(prepared.incident.title), 120)
        self.assertEqual(prepared.incident.description, description)

    def test_location_without_mapping_goes_to_central(self):
        self.assertEqual(transform(row(location_id="COL-10")).incident.branch.value, "central")
        self.assertEqual(transform(row(location_id="")).incident.branch.value, "central")
        self.assertEqual(transform(row(location_id="ESP-01")).incident.branch.value, "central")

    def test_invalid_date_cannot_be_transformed(self):
        for date in ["14/01/2024", "2024-13-01", ""]:
            with self.assertRaises(TransformError):
                transform(row(date=date))

    def test_missing_incident_id_uses_title_and_date(self):
        prepared = transform(row(incident_id=""))
        self.assertEqual(prepared.source_id, "Porción servida menor a la estándar del menú|2024-01-14T00:00:00+00:00")


class SeedTest(TempRepositoryTest):
    def test_full_csv_inserts_the_96_valid_rows_with_the_expected_totals(self):
        result = seed(load_records(CSV_PATH), self.repository)
        self.assertEqual((result.total, result.inserted, result.skipped), (100, 96, 0))
        self.assertEqual([incident_id for incident_id, _, _ in result.invalid], EXPECTED_INVALID)

        summary = self.repository.summary()
        self.assertEqual(summary.total, 96)
        self.assertEqual({key.value: count for key, count in summary.by_status.items()}, EXPECTED_STATUS)
        self.assertEqual({key.value: count for key, count in summary.by_category.items()}, EXPECTED_CATEGORY)
        self.assertEqual(summary.by_origin["customer"], 96)

    def test_invalid_rows_are_not_inserted_and_report_their_reason(self):
        result = seed(load_records(CSV_PATH), self.repository)
        reasons = {incident_id: (row_number, rules) for incident_id, row_number, rules in result.invalid}
        self.assertEqual(reasons["BRS-000044"], (45, ["Missing location_id"]))
        stored_titles = {incident.title for incident in self.repository.list()}
        invalid_rows = [record for record in load_records(CSV_PATH) if record["incident_id"] in reasons]
        for record in invalid_rows:
            self.assertFalse(self.repository.is_seeded(record["incident_id"]))
        self.assertEqual(len(stored_titles & {record["description"] for record in invalid_rows if record["description"]}), 0)

    def test_running_twice_does_not_duplicate(self):
        records = load_records(CSV_PATH)
        seed(records, self.repository)
        second = seed(records, self.repository)
        self.assertEqual((second.inserted, second.skipped, len(second.invalid)), (0, 96, 4))
        self.assertEqual(len(self.repository.list()), 96)

    def test_rows_sharing_title_and_date_are_all_loaded(self):
        # En el CSV hay filas válidas con la misma descripción y fecha: se distinguen por incident_id.
        records = [row(incident_id="BRS-1"), row(incident_id="BRS-2")]
        self.assertEqual(seed(records, self.repository).inserted, 2)

    def test_dates_are_midnight_utc_and_updated_at_matches(self):
        seed([row()], self.repository)
        incident = self.repository.get(1)
        self.assertEqual(incident.created_at, datetime(2024, 1, 14, tzinfo=timezone.utc))
        self.assertEqual(incident.updated_at, incident.created_at)

    def test_row_that_cannot_be_transformed_is_reported(self):
        result = seed([row(date="14/01/2024")], self.repository)
        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.invalid[0][0], "BRS-900001")
        self.assertIn("Fecha no válida", result.invalid[0][2][0])


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "db.json"
        self.previous = os.environ.get(BRASALAND_DB_PATH_ENV)
        os.environ[BRASALAND_DB_PATH_ENV] = str(self.db_path)

    def tearDown(self):
        if self.previous is None:
            os.environ.pop(BRASALAND_DB_PATH_ENV, None)
        else:
            os.environ[BRASALAND_DB_PATH_ENV] = self.previous
        self.tmp.cleanup()

    def run_main(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = seed_script.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_default_csv_is_loaded_into_the_configured_database(self):
        code, out, _ = self.run_main([])
        self.assertEqual(code, 0)
        self.assertIn("Insertadas .......................  96", out)
        self.assertIn("BRS-000044 (fila 45): Missing location_id", out)
        # El script muestra la ruta resuelta (en Windows, sin nombres cortos como JUANDE~1).
        self.assertIn(str(self.db_path.resolve()), out)
        repository = IncidentRepository.from_path(self.db_path)
        self.assertEqual(repository.summary().total, 96)
        repository.close()

    def test_missing_file_is_reported_without_writing(self):
        code, _, err = self.run_main([str(Path(self.tmp.name) / "no-existe.csv")])
        self.assertEqual(code, 1)
        self.assertIn("No se encontró el archivo", err)
        self.assertFalse(self.db_path.exists())

    def test_file_without_the_csv_columns_is_rejected(self):
        bad = Path(self.tmp.name) / "malo.csv"
        bad.write_text("id,texto\n1,hola\n", encoding="utf-8")
        code, _, err = self.run_main([str(bad)])
        self.assertEqual(code, 1)
        self.assertIn("Missing columns", err)

    def test_too_many_arguments(self):
        code, _, err = self.run_main(["a.csv", "b.csv"])
        self.assertEqual(code, 2)
        self.assertIn("Uso:", err)


if __name__ == "__main__":
    unittest.main()
