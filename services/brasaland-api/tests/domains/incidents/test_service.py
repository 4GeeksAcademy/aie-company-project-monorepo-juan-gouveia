"""Pruebas del servicio de incidentes: lectura de archivos subidos y valores del briefing.

Las reglas de validación también las cubren las pruebas del script
(scripts/incident-report/test_analyze.py), que usa este mismo servicio.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from app.domains.incidents import service
from app.domains.incidents.exceptions import (
    EmptyFileError,
    IncidentFileError,
    InvalidEncodingError,
    MissingColumnsError,
    NoRecordsError,
)

SAMPLE = Path(__file__).resolve().parents[5] / "data" / "raw" / "incidents-brasaland.csv"
HEADER = ",".join(service.FIELDS)


def test_parse_upload_reads_briefing_sample():
    summary = service.analyze(service.parse_upload(SAMPLE.read_bytes()))
    assert (summary["total"], summary["valid"], summary["invalid"]) == (100, 96, 4)
    assert summary["categories"] == {
        "CUSTOMER_COMPLAINT": 29, "EQUIPMENT": 17, "SUPPLY": 22, "FOOD_QUALITY": 19, "STAFF": 9,
    }
    assert summary["statuses"] == {"OPEN": 32, "CLOSED": 50, "DISCARDED": 14}
    assert service.rounded_average(summary) == Decimal("3.46")


def test_parse_upload_accepts_bom():
    data = f"{HEADER}\nBRS-000001,2024-01-01,COL-01,STAFF,Con BOM,OPEN,,,MGR-01\n".encode("utf-8-sig")
    assert service.parse_upload(data)[0]["incident_id"] == "BRS-000001"


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (b"", EmptyFileError),
        ("incident_id,date\nBRS-1,2024\n".encode("latin-1") + b"\xe9", InvalidEncodingError),
        (b"incident_id,date\nBRS-000001,2024-01-01\n", MissingColumnsError),
        (f"{HEADER}\n".encode(), NoRecordsError),
    ],
)
def test_parse_upload_errors(data, error):
    with pytest.raises(error):
        service.parse_upload(data)


def test_errors_are_value_errors_for_the_script():
    assert issubclass(IncidentFileError, ValueError)


def test_missing_columns_lists_them():
    with pytest.raises(MissingColumnsError) as raised:
        service.parse_upload(b"incident_id,date\nBRS-000001,2024-01-01\n")
    assert raised.value.missing == ["location_id", "category", "description", "status",
                                    "customer_id", "satisfaction_score", "reporter_id"]


def test_export_csv_text():
    rows = service.build_export_rows(service.analyze(service.load_records(SAMPLE)))
    lines = service.export_csv_text(rows).splitlines()
    assert lines[0] == "metric,value,percentage"
    assert "category.STAFF,9,9.4" in lines
    assert "satisfaction.average,3.46," in lines
